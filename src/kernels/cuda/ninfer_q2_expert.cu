// NInfer-derived single-token D3/D4 schedule, adapted to Flash-Next Q2_0.
// Function organization follows the Apache-2.0 reference at
// reference/ninfer/src/ops/sparse_moe/decode/sparse_moe_decode_kernels.cu:
// dot_two_rows + sparse_moe_d3_path_tiled_kernel (gate/up and SiLU), followed
// by dot_fp32_rows + sparse_moe_d4_token_kernel (down projection). The Q2_0
// byte decoder, FP32 activation contract, and expert-only epilogue are adapted
// for Strata; NInfer's Q4/Q5/Q6/W8 codecs, shared route and residual epilogue
// are not copied. Preserve reference/ninfer/LICENSE (Apache-2.0) with this code.

#include "strata/kernels/ninfer_q2_expert.hpp"
#include "strata/kernels/native_mmvq.hpp"
#include "strata/kernels/q8_1_finite.hpp"

#include <cuda_fp16.h>
#include <cuda_runtime.h>

#include <cstdint>
#include <atomic>
#include <stdexcept>

namespace strata::kernels {
namespace {
constexpr int kHidden = 2560;
constexpr int kIntermediate = 640;
constexpr int kQ2Block = 64;
constexpr int kQ2Bytes = 18;
constexpr int kRowsPerCta = 4;
std::atomic_bool g_backend_enabled{false};
std::atomic_bool g_backend_strict{false};
std::atomic<uint64_t> g_dispatch_count{0};

__device__ __forceinline__ float q2_0_value(const uint8_t* row, int k) {
    const uint8_t* block = row + (k / kQ2Block) * kQ2Bytes;
    const float scale = __half2float(*reinterpret_cast<const __half*>(block));
    const int local = k % kQ2Block;
    const int code = (block[2 + local / 4] >> ((local & 3) * 2)) & 3;
    return static_cast<float>(code - 1) * scale;
}

__device__ __forceinline__ float warp_sum(float value) {
    for (int offset = 16; offset > 0; offset >>= 1) value += __shfl_down_sync(0xffffffffu, value, offset);
    return value;
}

__device__ __forceinline__ float dot_q2_f32(const uint8_t* row, const float* x, int width) {
    const int lane = threadIdx.x & 31;
    float acc = 0.0f;
    for (int k = lane; k < width; k += 32) acc = fmaf(q2_0_value(row, k), x[k], acc);
    return warp_sum(acc);
}

struct Q8_1Block { __half d; __half s; int8_t qs[32]; };
static_assert(sizeof(Q8_1Block) == 36, "Q8_1 block size");

__device__ __forceinline__ float warp_sum_xor(float value) {
    for (int offset = 16; offset > 0; offset >>= 1)
        value += __shfl_xor_sync(0xffffffffu, value, offset, 32);
    return value;
}

__device__ __forceinline__ float warp_max_xor(float value) {
    for (int offset = 16; offset > 0; offset >>= 1)
        value = fmaxf(value, __shfl_xor_sync(0xffffffffu, value, offset, 32));
    return value;
}

// One warp owns one Q8_1 block, matching native_swiglu_quantize_q8_1's
// arithmetic while allowing arbitrary entry counts in one launch. The public
// native helper intentionally caps columns at eight, which otherwise forced
// one launch per eight routed entries here.
__global__ void ninfer_swiglu_quantize_q8_1_many(const float* gate, const float* up,
                                                 Q8_1Block* output, int64_t values) {
    const int64_t i = static_cast<int64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i >= values) return;
    const float g = gate[i];
    const float value = __fmul_rn(__fdividef(g, __fadd_rn(1.0f, __expf(-g))), up[i]);
    const float amax = warp_max_xor(fabsf(value));
    const float sum = warp_sum_xor(value);
    const float scale = q8_1_finite(amax / 127.0f);
    output[i / 32].qs[i % 32] = q8_1_quant(value, scale, amax);
    if ((i % 32) == 0) {
        const half2 ds = q8_1_ds(scale, sum);
        output[i / 32].d = __low2half(ds);
        output[i / 32].s = __high2half(ds);
    }
}

__device__ __forceinline__ float dot_q2_q8_1(const uint8_t* row, const Q8_1Block* xq, int width) {
    const int lane = threadIdx.x & 31;
    float acc = 0.0f;
    for (int k = lane; k < width; k += 32) {
        const uint8_t* block = row + (k / kQ2Block) * kQ2Bytes;
        const float dw = __half2float(*reinterpret_cast<const __half*>(block));
        const int local = k % kQ2Block;
        const int code = (block[2 + local / 4] >> ((local & 3) * 2)) & 3;
        const Q8_1Block& xb = xq[k / 32];
        const float dx = __half2float(xb.d);
        const float product = static_cast<float>(code - 1) * static_cast<float>(xb.qs[k % 32]);
        acc = fmaf(dw * dx, product, acc);
    }
    return warp_sum(acc);
}

__global__ void d3_q2_0(const uint8_t* gate, const uint8_t* up, const float* x, float* hidden) {
    const int lane = threadIdx.x & 31;
    const int warp = threadIdx.x >> 5;
    const int row = static_cast<int>(blockIdx.x) * kRowsPerCta + warp;
    if (row >= kIntermediate) return;
    constexpr int row_bytes = kHidden / kQ2Block * kQ2Bytes;
    const float g = dot_q2_f32(gate + static_cast<size_t>(row) * row_bytes, x, kHidden);
    const float u = dot_q2_f32(up + static_cast<size_t>(row) * row_bytes, x, kHidden);
    if (lane == 0) {
        const float sig = g >= 0.0f ? 1.0f / (1.0f + expf(-g)) : expf(g) / (1.0f + expf(g));
        hidden[row] = (g * sig) * u;
    }
}

__global__ void d4_q2_0(const uint8_t* down, const float* hidden, float* output) {
    const int lane = threadIdx.x & 31;
    const int warp = threadIdx.x >> 5;
    const int row = static_cast<int>(blockIdx.x) * kRowsPerCta + warp;
    if (row >= kHidden) return;
    constexpr int row_bytes = kIntermediate / kQ2Block * kQ2Bytes;
    const float value = dot_q2_f32(down + static_cast<size_t>(row) * row_bytes, hidden, kIntermediate);
    if (lane == 0) output[row] = value;
}

__global__ void d3_q2_0_grouped(const unsigned long long* grp_ptr, const int32_t* grp_start,
                                const int32_t* n_groups, const int32_t* ent_tok,
                                const Q8_1Block* xq, NativeExpertLayout L,
                                float* gate, float* up, int64_t grid_groups) {
    const int lane = threadIdx.x & 31;
    const int warp = threadIdx.x >> 5;
    const int row = static_cast<int>(blockIdx.x) * kRowsPerCta + warp;
    if (row >= 2 * L.n_ff) return;
    const bool is_up = row >= L.n_ff;
    const int r = is_up ? row - static_cast<int>(L.n_ff) : row;
    float* dst = is_up ? up : gate;
    const size_t offset = (is_up ? L.up_off : 0) + static_cast<size_t>(r) * L.gu_row;
    const int group_count = *n_groups;
    for (int g = static_cast<int>(blockIdx.y); g < group_count; g += static_cast<int>(grid_groups)) {
        const auto* weights = reinterpret_cast<const uint8_t*>(grp_ptr[g]) + offset;
        for (int e = grp_start[g]; e < grp_start[g + 1]; ++e) {
            const float value = dot_q2_q8_1(weights, xq + static_cast<size_t>(ent_tok[e]) * (L.n_embd / 32),
                                             static_cast<int>(L.n_embd));
            if (lane == 0) dst[static_cast<size_t>(e) * L.n_ff + r] = value;
        }
    }
}

__global__ void d4_q2_0_grouped(const unsigned long long* grp_ptr, const int32_t* grp_start,
                                const int32_t* n_groups, const int32_t* ent_dst,
                                const Q8_1Block* hq, NativeExpertLayout L, float* output,
                                int64_t grid_groups) {
    const int lane = threadIdx.x & 31;
    const int warp = threadIdx.x >> 5;
    const int row = static_cast<int>(blockIdx.x) * kRowsPerCta + warp;
    if (row >= L.n_embd) return;
    const size_t offset = L.down_off + static_cast<size_t>(row) * L.d_row;
    const int group_count = *n_groups;
    for (int g = static_cast<int>(blockIdx.y); g < group_count; g += static_cast<int>(grid_groups)) {
        const auto* weights = reinterpret_cast<const uint8_t*>(grp_ptr[g]) + offset;
        for (int e = grp_start[g]; e < grp_start[g + 1]; ++e) {
            const float value = dot_q2_q8_1(weights, hq + static_cast<size_t>(e) * (L.n_ff / 32),
                                             static_cast<int>(L.n_ff));
            if (lane == 0) output[static_cast<size_t>(ent_dst[e]) * L.n_embd + row] = value;
        }
    }
}
} // namespace

size_t ninfer_q2_0_expert_workspace_bytes() noexcept { return kIntermediate * sizeof(float); }
void ninfer_q2_0_expert_backend_set(bool enabled, bool strict) noexcept {
    g_backend_strict.store(strict, std::memory_order_relaxed);
    g_backend_enabled.store(enabled, std::memory_order_relaxed);
}
bool ninfer_q2_0_expert_backend_enabled() noexcept { return g_backend_enabled.load(std::memory_order_relaxed); }
bool ninfer_q2_0_expert_backend_strict() noexcept { return g_backend_strict.load(std::memory_order_relaxed); }
uint64_t ninfer_q2_0_expert_dispatch_count() noexcept { return g_dispatch_count.load(std::memory_order_relaxed); }

void ninfer_q2_0_expert(const void* gate_q2_0, const void* up_q2_0, const void* down_q2_0,
                        const float* x, float* workspace, float* output, void* stream) {
    if (gate_q2_0 == nullptr || up_q2_0 == nullptr || down_q2_0 == nullptr || x == nullptr ||
        workspace == nullptr || output == nullptr) {
        throw std::invalid_argument("ninfer_q2_0_expert: null caller-owned buffer");
    }
    const auto s = static_cast<cudaStream_t>(stream);
    d3_q2_0<<<(kIntermediate + kRowsPerCta - 1) / kRowsPerCta, 128, 0, s>>>(
        static_cast<const uint8_t*>(gate_q2_0), static_cast<const uint8_t*>(up_q2_0), x, workspace);
    d4_q2_0<<<(kHidden + kRowsPerCta - 1) / kRowsPerCta, 128, 0, s>>>(
        static_cast<const uint8_t*>(down_q2_0), workspace, output);
    const cudaError_t error = cudaGetLastError();
    if (error != cudaSuccess) throw std::runtime_error(cudaGetErrorString(error));
}

void ninfer_q2_0_expert_grouped(const NativeExpertLayout& L, const unsigned long long* grp_ptr,
                               const int32_t* grp_start, const int32_t* n_groups,
                               const int32_t* ent_dst, const int32_t* ent_tok,
                               int64_t cap_groups, int64_t cap_entries, const void* x_q8_1,
                               void* workspace, float* output, void* stream, int64_t grid_groups) {
    if (L.gu_type != 42 || L.d_type != 42 || L.n_embd != kHidden || L.n_ff != kIntermediate ||
        cap_groups <= 0 || cap_entries <= 0 || grp_ptr == nullptr || grp_start == nullptr || n_groups == nullptr ||
        ent_dst == nullptr || ent_tok == nullptr || x_q8_1 == nullptr || workspace == nullptr || output == nullptr) {
        throw std::invalid_argument("ninfer_q2_0_expert_grouped: unsupported profile or null caller-owned buffer");
    }
    g_dispatch_count.fetch_add(1, std::memory_order_relaxed);
    const int64_t gy = grid_groups <= 0 || grid_groups > cap_groups ? cap_groups : grid_groups;
    const size_t f = static_cast<size_t>(cap_entries) * kIntermediate * sizeof(float);
    const size_t fa = (f + 255) & ~size_t(255);
    auto* scratch = static_cast<uint8_t*>(workspace);
    auto* gate = reinterpret_cast<float*>(scratch);
    auto* up = reinterpret_cast<float*>(scratch + fa);
    auto* hidden_q8_1 = scratch + 3 * fa;
    const auto s = static_cast<cudaStream_t>(stream);
    d3_q2_0_grouped<<<dim3((2 * kIntermediate + kRowsPerCta - 1) / kRowsPerCta, static_cast<unsigned>(gy)),
                       128, 0, s>>>(grp_ptr, grp_start, n_groups, ent_tok,
                                     static_cast<const Q8_1Block*>(x_q8_1), L, gate, up, gy);
    const int64_t hidden_values = cap_entries * kIntermediate;
    ninfer_swiglu_quantize_q8_1_many<<<static_cast<unsigned>((hidden_values + 255) / 256), 256, 0, s>>>(
        gate, up, reinterpret_cast<Q8_1Block*>(hidden_q8_1), hidden_values);
    d4_q2_0_grouped<<<dim3((kHidden + kRowsPerCta - 1) / kRowsPerCta, static_cast<unsigned>(gy)),
                       128, 0, s>>>(grp_ptr, grp_start, n_groups, ent_dst,
                                     reinterpret_cast<const Q8_1Block*>(hidden_q8_1), L, output, gy);
    const cudaError_t error = cudaGetLastError();
    if (error != cudaSuccess) throw std::runtime_error(cudaGetErrorString(error));
}

} // namespace strata::kernels

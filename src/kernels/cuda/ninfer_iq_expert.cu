// NInfer D3/D4 grouped schedule adaptation for Flash-Next IQ mixed-codec pairs.
// Schedule provenance: Apache-2.0 reference/ninfer/src/ops/sparse_moe/decode/
// sparse_moe_decode_kernels.cu. Codec blocks and canonical tables follow the
// pinned ggml implementation (MIT, third_party/ggml/LICENSE); Strata routing,
// shared-expert, route-weight and residual epilogues are not copied.

#include "strata/kernels/ninfer_iq_expert.hpp"
#include "strata/kernels/dp4a.hpp"
#include "strata/kernels/q8_1_finite.hpp"

#include <cuda_fp16.h>
#include <cuda_runtime.h>

#define GGML_COMMON_DECL_CUDA
#define GGML_COMMON_IMPL_CUDA
#include "ggml-common.h"

#include <atomic>
#include <cstdint>
#include <stdexcept>

namespace strata::kernels {
namespace {
constexpr int kHidden = 2560;
constexpr int kIntermediate = 640;
constexpr int kRowsPerCta = 4;
struct Q8_1Block { __half d; __half s; int8_t qs[32]; };
static_assert(sizeof(Q8_1Block) == 36, "Q8_1 block ABI");
std::atomic_bool g_enabled{false};
std::atomic<uint64_t> g_dispatch_count{0};
std::atomic_bool g_iq3xxs_enabled{false};
std::atomic<uint64_t> g_iq3xxs_dispatch_count{0};
std::atomic_bool g_iq3s_enabled{false};
std::atomic<uint64_t> g_iq3s_dispatch_count{0};

__device__ __forceinline__ float warp_sum(float value) {
    for (int offset = 16; offset > 0; offset >>= 1)
        value += __shfl_down_sync(0xffffffffu, value, offset);
    return value;
}

__device__ __forceinline__ float warp_sum_xor(float value) {
    for (int offset = 16; offset > 0; offset >>= 1)
        value += __shfl_xor_sync(0xffffffffu, value, offset);
    return value;
}

__device__ __forceinline__ float warp_max_xor(float value) {
    for (int offset = 16; offset > 0; offset >>= 1)
        value = fmaxf(value, __shfl_xor_sync(0xffffffffu, value, offset));
    return value;
}

// One lane owns each eight-code IQ2_S subgroup. Its grid and sign byte cover
// eight values; two packed Q8_1 words contribute those values to the integer
// subtotal. This mirrors the GGML Q8_1 dot contract without calling Strata's
// existing grouped IQ expert operator.
__device__ __forceinline__ float iq2s_q8_1_block(const uint8_t* weight,
                                                 const Q8_1Block* activation,
                                                 int subgroup32) {
    const auto* block = reinterpret_cast<const block_iq2_s*>(weight);
    const int group = subgroup32;
    const float d = __half2float(block->d);
    const int ls0 = block->scales[group] & 0x0f;
    const int ls1 = block->scales[group] >> 4;
    int sum0 = 0, sum1 = 0;
#pragma unroll
    for (int sub = 0; sub < 4; ++sub) {
        const int qindex = 4 * group + sub;
        const int grid_index = block->qs[qindex] | ((block->qh[group] << (8 - 2 * sub)) & 0x300);
        const uint64_t pattern = iq2s_grid[grid_index];
        const uint8_t signs = block->qs[32 + qindex];
        const int q8_offset = sub * 2;
        const int* q8 = reinterpret_cast<const int*>(activation->qs) + q8_offset;
        const int packed0 = static_cast<int>((pattern >> 0) & 0xffffffffu);
        const int packed1 = static_cast<int>((pattern >> 32) & 0xffffffffu);
        int sign0 = 0, sign1 = 0;
#pragma unroll
        for (int i = 0; i < 4; ++i) {
            if (signs & (1u << i)) sign0 |= 0xffu << (i * 8);
            if (signs & (1u << (i + 4))) sign1 |= 0xffu << (i * 8);
        }
        const int signed0 = __vsub4(packed0 ^ sign0, sign0);
        const int signed1 = __vsub4(packed1 ^ sign1, sign1);
        const int subtotal = STRATA_DP4A(signed0, q8[0], 0) + STRATA_DP4A(signed1, q8[1], 0);
        if (sub < 2) sum0 += subtotal;
        else sum1 += subtotal;
    }
    // Each 32-value Q8 block uses four eight-value IQ2_S subgroups. The two
    // scale nibbles apply to subgroup pairs; scale rounding is integer as in
    // GGML before the two FP16 scales are multiplied.
    const int scaled = (sum0 * ls0 + sum1 * ls1 + (sum0 + sum1) / 2) / 4;
    return d * __half2float(activation->d) * static_cast<float>(scaled);
}

__device__ __forceinline__ float dot_iq2s_q8_1(const uint8_t* row,
                                                const Q8_1Block* xq,
                                                int width) {
    const int lane = threadIdx.x & 31;
    const int blocks = width / 32;
    float total = 0.0f;
    for (int b = lane; b < blocks; b += 32) {
        const int super = b / 8;
        const int sub = b & 7;
        total += iq2s_q8_1_block(row + super * sizeof(block_iq2_s), xq + b, sub);
    }
    return warp_sum(total);
}

__device__ __forceinline__ float iq3xxs_q8_1_block(const uint8_t* weight,
                                                    const Q8_1Block* activation,
                                                    int subgroup) {
    const auto* block = reinterpret_cast<const block_iq3_xxs*>(weight);
    const int iqs = 2 * subgroup;
    const uint16_t* q16 = reinterpret_cast<const uint16_t*>(block->qs);
    const int q0 = static_cast<int>(q16[2 * iqs]) | (static_cast<int>(q16[2 * iqs + 1]) << 16);
    const int q1 = static_cast<int>(q16[2 * (iqs + 1)]) | (static_cast<int>(q16[2 * (iqs + 1) + 1]) << 16);
    const int2 q3_packed = make_int2(q0, q1);
    const uint8_t* q3 = reinterpret_cast<const uint8_t*>(&q3_packed);
    const int aux_index = 16 + iqs / 2;
    const uint32_t aux = static_cast<uint32_t>(q16[2 * aux_index]) |
                         (static_cast<uint32_t>(q16[2 * aux_index + 1]) << 16);
    int sum = 0;
#pragma unroll
    for (int l0 = 0; l0 < 8; l0 += 2) {
        const int2 grid_pos = make_int2(iq3xxs_grid[q3[l0]], iq3xxs_grid[q3[l0 + 1]]);
        const uint8_t shifted = static_cast<uint8_t>(aux >> (7 * l0 / 2));
        const uint32_t parity = __popc(static_cast<uint32_t>(shifted)) & 1u;
        const uint32_t signs = (static_cast<uint32_t>(shifted) ^ (parity << 7)) * 0x01010101u;
        const int signs0 = __vcmpne4(signs & 0x08040201, 0);
        const int grid_l = __vsub4(grid_pos.x ^ signs0, signs0);
        const int signs1 = __vcmpne4(signs & 0x80402010, 0);
        const int grid_h = __vsub4(grid_pos.y ^ signs1, signs1);
        const int* q8 = reinterpret_cast<const int*>(activation->qs);
        sum = STRATA_DP4A(grid_l, q8[l0], sum);
        sum = STRATA_DP4A(grid_h, q8[l0 + 1], sum);
    }
    const int scale = aux >> 28;
    const int scaled = (scale * sum + sum / 2) / 2;
    return __half2float(block->d) * __half2float(activation->d) * static_cast<float>(scaled);
}

__device__ __forceinline__ float dot_iq3xxs_q8_1(const uint8_t* row,
                                                  const Q8_1Block* xq,
                                                  int width) {
    const int lane = threadIdx.x & 31;
    const int blocks = width / 32;
    float total = 0.0f;
    for (int b = lane; b < blocks; b += 32) {
        const int super = b / 8;
        const int sub = b & 7;
        total += iq3xxs_q8_1_block(row + super * sizeof(block_iq3_xxs), xq + b, sub);
    }
    return warp_sum(total);
}

__device__ __forceinline__ float iq3s_q8_1_block(const uint8_t* weight,
                                                  const Q8_1Block* activation,
                                                  int subgroup) {
    const auto* block = reinterpret_cast<const block_iq3_s*>(weight);
    const int iqs = 2 * subgroup;
    const uint16_t* q16 = reinterpret_cast<const uint16_t*>(block->qs);
    const int q0 = static_cast<int>(q16[2 * iqs]) | (static_cast<int>(q16[2 * iqs + 1]) << 16);
    const int q1 = static_cast<int>(q16[2 * (iqs + 1)]) | (static_cast<int>(q16[2 * (iqs + 1) + 1]) << 16);
    const int2 q_packed = make_int2(q0, q1);
    const uint8_t* qs = reinterpret_cast<const uint8_t*>(&q_packed);
    const int qh = block->qh[subgroup];
    const uint16_t* signs16 = reinterpret_cast<const uint16_t*>(block->signs);
    const uint32_t signs32 = static_cast<uint32_t>(signs16[2 * subgroup]) |
                             (static_cast<uint32_t>(signs16[2 * subgroup + 1]) << 16);
    const uint8_t* signs8 = reinterpret_cast<const uint8_t*>(&signs32);
    const int* q8 = reinterpret_cast<const int*>(activation->qs);
    int sum = 0;
#pragma unroll
    for (int l0 = 0; l0 < 8; l0 += 2) {
        const int2 grid = make_int2(iq3s_grid[qs[l0] | ((qh << (8 - l0)) & 0x100)],
                                    iq3s_grid[qs[l0 + 1] | ((qh << (7 - l0)) & 0x100)]);
        const uint32_t packed = signs8[l0 / 2];
        const int signs0 = __vcmpne4(((packed & 0x03) << 7) | ((packed & 0x0c) << 21), 0);
        const int signs1 = __vcmpne4(((packed & 0x30) << 3) | ((packed & 0xc0) << 17), 0);
        const int grid_l = __vsub4(grid.x ^ signs0, signs0);
        const int grid_h = __vsub4(grid.y ^ signs1, signs1);
        sum = STRATA_DP4A(grid_l, q8[l0], sum);
        sum = STRATA_DP4A(grid_h, q8[l0 + 1], sum);
    }
    const int scale_byte = block->scales[subgroup / 2];
    const int scale = 1 + 2 * ((scale_byte >> ((subgroup & 1) * 4)) & 0x0f);
    sum *= scale;
    return __half2float(block->d) * __half2float(activation->d) * static_cast<float>(sum);
}

__device__ __forceinline__ float dot_iq3s_q8_1(const uint8_t* row,
                                                const Q8_1Block* xq,
                                                int width) {
    const int lane = threadIdx.x & 31;
    const int blocks = width / 32;
    float total = 0.0f;
    for (int b = lane; b < blocks; b += 32) {
        const int super = b / 8;
        total += iq3s_q8_1_block(row + super * sizeof(block_iq3_s), xq + b, b & 7);
    }
    return warp_sum(total);
}

__device__ __forceinline__ float dot_iq4nl_q8_1(const uint8_t* row,
                                                 const Q8_1Block* xq,
                                                 int width) {
    const int lane = threadIdx.x & 31;
    const int blocks = width / 32;
    float total = 0.0f;
    for (int b = lane; b < blocks; b += 32) {
        const auto* w = reinterpret_cast<const block_iq4_nl*>(row) + b;
        int subtotal = 0;
#pragma unroll
        for (int group = 0; group < 4; ++group) {
#pragma unroll
            for (int j = 0; j < 4; ++j) {
                const uint8_t packed = w->qs[4 * group + j];
                const int lo = kvalues_iq4nl[packed & 0x0f];
                const int hi = kvalues_iq4nl[packed >> 4];
                subtotal += lo * reinterpret_cast<const int8_t*>(xq[b].qs)[4 * group + j];
                subtotal += hi * reinterpret_cast<const int8_t*>(xq[b].qs)[16 + 4 * group + j];
            }
        }
        total += __half2float(w->d) * __half2float(xq[b].d) * static_cast<float>(subtotal);
    }
    return warp_sum(total);
}

__global__ void d3_iq2s_grouped(const unsigned long long* grp_ptr,
                               const int32_t* grp_start, const int32_t* n_groups,
                               const int32_t* ent_tok, const Q8_1Block* xq,
                               NativeExpertLayout L, float* gate, float* up,
                               int64_t grid_groups) {
    const int lane = threadIdx.x & 31;
    const int warp = threadIdx.x >> 5;
    const int row = static_cast<int>(blockIdx.x) * kRowsPerCta + warp;
    if (row >= 2 * L.n_ff) return;
    const bool is_up = row >= L.n_ff;
    const int r = is_up ? row - static_cast<int>(L.n_ff) : row;
    float* dst = is_up ? up : gate;
    const size_t offset = (is_up ? L.up_off : 0) + static_cast<size_t>(r) * L.gu_row;
    for (int g = static_cast<int>(blockIdx.y); g < *n_groups; g += static_cast<int>(grid_groups)) {
        const auto* weights = reinterpret_cast<const uint8_t*>(grp_ptr[g]) + offset;
        for (int e = grp_start[g]; e < grp_start[g + 1]; ++e) {
            const auto* activation = xq + static_cast<size_t>(ent_tok[e]) * (L.n_embd / 32);
            const float value = dot_iq2s_q8_1(weights, activation, static_cast<int>(L.n_embd));
            if (lane == 0) dst[static_cast<size_t>(e) * L.n_ff + r] = value;
        }
    }
}

__global__ void d3_iq3xxs_grouped(const unsigned long long* grp_ptr,
                                  const int32_t* grp_start, const int32_t* n_groups,
                                  const int32_t* ent_tok, const Q8_1Block* xq,
                                  NativeExpertLayout L, float* gate, float* up,
                                  int64_t grid_groups) {
    const int lane = threadIdx.x & 31;
    const int warp = threadIdx.x >> 5;
    const int row = static_cast<int>(blockIdx.x) * kRowsPerCta + warp;
    if (row >= 2 * L.n_ff) return;
    const bool is_up = row >= L.n_ff;
    const int r = is_up ? row - static_cast<int>(L.n_ff) : row;
    float* dst = is_up ? up : gate;
    const size_t offset = (is_up ? L.up_off : 0) + static_cast<size_t>(r) * L.gu_row;
    for (int g = static_cast<int>(blockIdx.y); g < *n_groups; g += static_cast<int>(grid_groups)) {
        const auto* weights = reinterpret_cast<const uint8_t*>(grp_ptr[g]) + offset;
        for (int e = grp_start[g]; e < grp_start[g + 1]; ++e) {
            const auto* activation = xq + static_cast<size_t>(ent_tok[e]) * (L.n_embd / 32);
            const float value = dot_iq3xxs_q8_1(weights, activation, static_cast<int>(L.n_embd));
            if (lane == 0) dst[static_cast<size_t>(e) * L.n_ff + r] = value;
        }
    }
}

__global__ void d3_iq3s_grouped(const unsigned long long* grp_ptr,
                                const int32_t* grp_start, const int32_t* n_groups,
                                const int32_t* ent_tok, const Q8_1Block* xq,
                                NativeExpertLayout L, float* gate, float* up,
                                int64_t grid_groups) {
    const int lane = threadIdx.x & 31;
    const int warp = threadIdx.x >> 5;
    const int row = static_cast<int>(blockIdx.x) * kRowsPerCta + warp;
    if (row >= 2 * L.n_ff) return;
    const bool is_up = row >= L.n_ff;
    const int r = is_up ? row - static_cast<int>(L.n_ff) : row;
    float* dst = is_up ? up : gate;
    const size_t offset = (is_up ? L.up_off : 0) + static_cast<size_t>(r) * L.gu_row;
    for (int g = static_cast<int>(blockIdx.y); g < *n_groups; g += static_cast<int>(grid_groups)) {
        const auto* weights = reinterpret_cast<const uint8_t*>(grp_ptr[g]) + offset;
        for (int e = grp_start[g]; e < grp_start[g + 1]; ++e) {
            const auto* activation = xq + static_cast<size_t>(ent_tok[e]) * (L.n_embd / 32);
            const float value = dot_iq3s_q8_1(weights, activation, static_cast<int>(L.n_embd));
            if (lane == 0) dst[static_cast<size_t>(e) * L.n_ff + r] = value;
        }
    }
}

__global__ void swiglu_quantize(const float* gate, const float* up,
                                Q8_1Block* output, int64_t values) {
    const int64_t i = static_cast<int64_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i >= values) return;
    const float g = gate[i];
    const float h = __fmul_rn(g / (1.0f + __expf(-g)), up[i]);
    const float amax = warp_max_xor(fabsf(h));
    const float sum = warp_sum_xor(h);
    const float scale = q8_1_finite(amax / 127.0f);
    output[i / 32].qs[i % 32] = q8_1_quant(h, scale, amax);
    if ((i % 32) == 0) {
        const half2 ds = q8_1_ds(scale, sum);
        output[i / 32].d = __low2half(ds);
        output[i / 32].s = __high2half(ds);
    }
}

__global__ void d4_iq4nl_grouped(const unsigned long long* grp_ptr,
                                const int32_t* grp_start, const int32_t* n_groups,
                                const int32_t* ent_dst, const Q8_1Block* hq,
                                NativeExpertLayout L, float* output,
                                int64_t grid_groups) {
    const int lane = threadIdx.x & 31;
    const int warp = threadIdx.x >> 5;
    const int row = static_cast<int>(blockIdx.x) * kRowsPerCta + warp;
    if (row >= L.n_embd) return;
    const size_t offset = L.down_off + static_cast<size_t>(row) * L.d_row;
    for (int g = static_cast<int>(blockIdx.y); g < *n_groups; g += static_cast<int>(grid_groups)) {
        const auto* weights = reinterpret_cast<const uint8_t*>(grp_ptr[g]) + offset;
        for (int e = grp_start[g]; e < grp_start[g + 1]; ++e) {
            const auto* hidden = hq + static_cast<size_t>(e) * (L.n_ff / 32);
            const float value = dot_iq4nl_q8_1(weights, hidden, static_cast<int>(L.n_ff));
            if (lane == 0) output[static_cast<size_t>(ent_dst[e]) * L.n_embd + row] = value;
        }
    }
}
} // namespace

size_t ninfer_iq2s_iq4nl_workspace_bytes(int64_t cap_entries, int64_t n_ff) noexcept {
    if (cap_entries <= 0 || n_ff <= 0) return 0;
    const size_t f = static_cast<size_t>(cap_entries) * static_cast<size_t>(n_ff) * sizeof(float);
    const size_t fa = (f + 255) & ~size_t(255);
    const size_t q = static_cast<size_t>(cap_entries) * static_cast<size_t>(n_ff / 32) * sizeof(Q8_1Block);
    const size_t qa = (q + 255) & ~size_t(255);
    return 3 * fa + qa;
}

void ninfer_iq2s_iq4nl_backend_set(bool enabled) noexcept { g_enabled.store(enabled); }
bool ninfer_iq2s_iq4nl_backend_enabled() noexcept { return g_enabled.load(); }
uint64_t ninfer_iq2s_iq4nl_dispatch_count() noexcept { return g_dispatch_count.load(); }
void ninfer_iq3xxs_iq4nl_backend_set(bool enabled) noexcept { g_iq3xxs_enabled.store(enabled); }
bool ninfer_iq3xxs_iq4nl_backend_enabled() noexcept { return g_iq3xxs_enabled.load(); }
uint64_t ninfer_iq3xxs_iq4nl_dispatch_count() noexcept { return g_iq3xxs_dispatch_count.load(); }
void ninfer_iq3s_iq4nl_backend_set(bool enabled) noexcept { g_iq3s_enabled.store(enabled); }
bool ninfer_iq3s_iq4nl_backend_enabled() noexcept { return g_iq3s_enabled.load(); }
uint64_t ninfer_iq3s_iq4nl_dispatch_count() noexcept { return g_iq3s_dispatch_count.load(); }

void ninfer_iq2s_iq4nl_expert_grouped(const NativeExpertLayout& L,
                                     const unsigned long long* grp_ptr,
                                     const int32_t* grp_start,
                                     const int32_t* n_groups,
                                     const int32_t* ent_dst,
                                     const int32_t* ent_tok,
                                     int64_t cap_groups,
                                     int64_t cap_entries,
                                     const void* x_q8_1,
                                     void* workspace,
                                     float* output,
                                     void* stream,
                                     int64_t grid_groups) {
    if (L.gu_type != 22 || L.d_type != 20 || L.n_embd != kHidden || L.n_ff != kIntermediate ||
        cap_groups <= 0 || cap_entries <= 0 || !grp_ptr || !grp_start || !n_groups || !ent_dst || !ent_tok ||
        !x_q8_1 || !workspace || !output)
        throw std::invalid_argument("ninfer_iq2s_iq4nl_expert_grouped: unsupported profile or null buffer");
    g_dispatch_count.fetch_add(1, std::memory_order_relaxed);
    const int64_t gy = grid_groups <= 0 || grid_groups > cap_groups ? cap_groups : grid_groups;
    const size_t f = static_cast<size_t>(cap_entries) * kIntermediate * sizeof(float);
    const size_t fa = (f + 255) & ~size_t(255);
    auto* scratch = static_cast<uint8_t*>(workspace);
    auto* gate = reinterpret_cast<float*>(scratch);
    auto* up = reinterpret_cast<float*>(scratch + fa);
    auto* hidden = reinterpret_cast<Q8_1Block*>(scratch + 3 * fa);
    const auto s = static_cast<cudaStream_t>(stream);
    d3_iq2s_grouped<<<dim3((2 * kIntermediate + kRowsPerCta - 1) / kRowsPerCta,
                            static_cast<unsigned>(gy)), 128, 0, s>>>(
        grp_ptr, grp_start, n_groups, ent_tok, static_cast<const Q8_1Block*>(x_q8_1), L, gate, up, gy);
    const int64_t values = cap_entries * kIntermediate;
    swiglu_quantize<<<static_cast<unsigned>((values + 255) / 256), 256, 0, s>>>(gate, up, hidden, values);
    d4_iq4nl_grouped<<<dim3((kHidden + kRowsPerCta - 1) / kRowsPerCta,
                             static_cast<unsigned>(gy)), 128, 0, s>>>(
        grp_ptr, grp_start, n_groups, ent_dst, hidden, L, output, gy);
    const cudaError_t error = cudaGetLastError();
    if (error != cudaSuccess) throw std::runtime_error(cudaGetErrorString(error));
}

void ninfer_iq3xxs_iq4nl_expert_grouped(const NativeExpertLayout& L,
                                        const unsigned long long* grp_ptr,
                                        const int32_t* grp_start,
                                        const int32_t* n_groups,
                                        const int32_t* ent_dst,
                                        const int32_t* ent_tok,
                                        int64_t cap_groups,
                                        int64_t cap_entries,
                                        const void* x_q8_1,
                                        void* workspace,
                                        float* output,
                                        void* stream,
                                        int64_t grid_groups) {
    if (L.gu_type != 18 || L.d_type != 20 || L.n_embd != kHidden || L.n_ff != kIntermediate ||
        cap_groups <= 0 || cap_entries <= 0 || !grp_ptr || !grp_start || !n_groups || !ent_dst || !ent_tok ||
        !x_q8_1 || !workspace || !output)
        throw std::invalid_argument("ninfer_iq3xxs_iq4nl_expert_grouped: unsupported profile or null buffer");
    g_iq3xxs_dispatch_count.fetch_add(1, std::memory_order_relaxed);
    const int64_t gy = grid_groups <= 0 || grid_groups > cap_groups ? cap_groups : grid_groups;
    const size_t f = static_cast<size_t>(cap_entries) * kIntermediate * sizeof(float);
    const size_t fa = (f + 255) & ~size_t(255);
    auto* scratch = static_cast<uint8_t*>(workspace);
    auto* gate = reinterpret_cast<float*>(scratch);
    auto* up = reinterpret_cast<float*>(scratch + fa);
    auto* hidden = reinterpret_cast<Q8_1Block*>(scratch + 3 * fa);
    const auto s = static_cast<cudaStream_t>(stream);
    d3_iq3xxs_grouped<<<dim3((2 * kIntermediate + kRowsPerCta - 1) / kRowsPerCta,
                              static_cast<unsigned>(gy)), 128, 0, s>>>(
        grp_ptr, grp_start, n_groups, ent_tok, static_cast<const Q8_1Block*>(x_q8_1), L, gate, up, gy);
    const int64_t values = cap_entries * kIntermediate;
    swiglu_quantize<<<static_cast<unsigned>((values + 255) / 256), 256, 0, s>>>(gate, up, hidden, values);
    d4_iq4nl_grouped<<<dim3((kHidden + kRowsPerCta - 1) / kRowsPerCta,
                             static_cast<unsigned>(gy)), 128, 0, s>>>(
        grp_ptr, grp_start, n_groups, ent_dst, hidden, L, output, gy);
    const cudaError_t error = cudaGetLastError();
    if (error != cudaSuccess) throw std::runtime_error(cudaGetErrorString(error));
}

void ninfer_iq3s_iq4nl_expert_grouped(const NativeExpertLayout& L,
                                      const unsigned long long* grp_ptr,
                                      const int32_t* grp_start,
                                      const int32_t* n_groups,
                                      const int32_t* ent_dst,
                                      const int32_t* ent_tok,
                                      int64_t cap_groups,
                                      int64_t cap_entries,
                                      const void* x_q8_1,
                                      void* workspace,
                                      float* output,
                                      void* stream,
                                      int64_t grid_groups) {
    if (L.gu_type != 21 || L.d_type != 20 || L.n_embd != kHidden || L.n_ff != kIntermediate ||
        cap_groups <= 0 || cap_entries <= 0 || !grp_ptr || !grp_start || !n_groups || !ent_dst || !ent_tok ||
        !x_q8_1 || !workspace || !output)
        throw std::invalid_argument("ninfer_iq3s_iq4nl_expert_grouped: unsupported profile or null buffer");
    g_iq3s_dispatch_count.fetch_add(1, std::memory_order_relaxed);
    const int64_t gy = grid_groups <= 0 || grid_groups > cap_groups ? cap_groups : grid_groups;
    const size_t f = static_cast<size_t>(cap_entries) * kIntermediate * sizeof(float);
    const size_t fa = (f + 255) & ~size_t(255);
    auto* scratch = static_cast<uint8_t*>(workspace);
    auto* gate = reinterpret_cast<float*>(scratch);
    auto* up = reinterpret_cast<float*>(scratch + fa);
    auto* hidden = reinterpret_cast<Q8_1Block*>(scratch + 3 * fa);
    const auto s = static_cast<cudaStream_t>(stream);
    d3_iq3s_grouped<<<dim3((2 * kIntermediate + kRowsPerCta - 1) / kRowsPerCta,
                            static_cast<unsigned>(gy)), 128, 0, s>>>(
        grp_ptr, grp_start, n_groups, ent_tok, static_cast<const Q8_1Block*>(x_q8_1), L, gate, up, gy);
    const int64_t values = cap_entries * kIntermediate;
    swiglu_quantize<<<static_cast<unsigned>((values + 255) / 256), 256, 0, s>>>(gate, up, hidden, values);
    d4_iq4nl_grouped<<<dim3((kHidden + kRowsPerCta - 1) / kRowsPerCta,
                             static_cast<unsigned>(gy)), 128, 0, s>>>(
        grp_ptr, grp_start, n_groups, ent_dst, hidden, L, output, gy);
    const cudaError_t error = cudaGetLastError();
    if (error != cudaSuccess) throw std::runtime_error(cudaGetErrorString(error));
}

} // namespace strata::kernels

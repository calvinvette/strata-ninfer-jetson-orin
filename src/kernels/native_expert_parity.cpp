#include "strata/platform/cpu_arch.hpp"
// src/kernels/native_expert_parity.cpp - plan v0.3 P6: one native expert three ways.
//
//     build/native_expert_parity <shard.gguf> [layer ...]     real rows (a split model's shards are found by name)
//     build/native_expert_parity --synthetic GU/DOWN ...      random weights quantized by ggml (e.g. q4_K/q5_1)
//     build/native_expert_parity --q5_1-min                   the Q5_1 min term on crafted activations
//
// (a) float reference: ggml's own dequantizer (`to_float`) and a float SwiGLU expert, (b) the CPU path
// (ggml-cpu vec_dot with its quantized activations), (c) the GPU path (`native_expert_grouped`, q8_1
// activations).  (b) and (c) each differ from (a) by their activation rounding only (a few 1e-3 relative).  (c) runs
// twice, with the kernels that decode a weight part once for all entries and with the per-entry ones: bitwise equal.
// (d) the GPU dequantizers of the prompt path and the embedding against `to_float` (Q8_0: bit for bit).
// The synthetic mode and (d) follow eddoursul/Strata 8029fa9.
#include "strata/artifact/gguf_reader.hpp"
#include "strata/kernels/cpu/native_expert.hpp"
#include "strata/kernels/cpu/expert.hpp"
#include "strata/kernels/cpu/iq_avx512.hpp"
#include "strata/kernels/cpu/iq_avx2.hpp"
#include "strata/kernels/cpu/kq_avx2.hpp"
#include "strata/kernels/cpu/expert_layout.hpp"
#include "ggml-cpu.h"
#include "strata/kernels/iq_kernels.hpp"
#include "strata/kernels/native_mmvq.hpp"

#include "ggml.h"

#define GGML_COMMON_DECL_CPP
#define GGML_COMMON_IMPL_CPP
#include "../../third_party/ggml/ggml-common.h"

#include <cuda_runtime.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <random>
#include <string>
#include <vector>

namespace cpu = strata::kernels::cpu;

namespace {
struct ParityQ81 { ggml_fp16_t d, s; int8_t qs[32]; };
static_assert(sizeof(ParityQ81) == 36, "Q8_1 block layout");

// Independent harness transcription of the packed IQ2_S/Q8_1 CPU mirror. The
// caller validates its reconstructed SwiGLU row against native_gu_rows output.
float parity_iq2_s_q8_1_dot(const uint8_t* row, const uint8_t* xq, int n) {
    if (n % QK_K != 0) std::abort();
    const int nb = n / QK_K;
    std::array<float, 32> lane_sum{};
    for (int lane = 0; lane < 32; ++lane) {
        for (int k = lane; k < nb * 8; k += 32) {
            const int kbx = k / 8;
            const int iqs = 2 * (k % 8);
            const auto* w = reinterpret_cast<const block_iq2_s*>(row) + kbx;
            const auto* x = reinterpret_cast<const ParityQ81*>(xq) + kbx * 8 + iqs / 2;
            const uint8_t* qs = w->qs + 4 * (iqs / 2);
            const uint8_t qh = w->qh[iqs / 2];
            const uint8_t* signs = w->qs + 32 + 4 * (iqs / 2);
            const int ls0 = w->scales[iqs / 2] & 0x0f;
            const int ls1 = w->scales[iqs / 2] >> 4;
            int sumi0 = 0, sumi1 = 0;
            for (int l0 = 0; l0 < 8; l0 += 2) {
                const uint64_t grid = iq2s_grid[qs[l0 / 2] | ((qh << (8 - l0)) & 0x300)];
                const uint8_t sign = signs[l0 / 2];
                const int q8_offset = l0 * 4;
                for (int j = 0; j < 4; ++j) {
                    int lo = (int) ((grid >> (8 * j)) & 0xff);
                    int hi = (int) ((grid >> (8 * (j + 4))) & 0xff);
                    if ((sign >> j) & 1) lo = -lo;
                    if ((sign >> (j + 4)) & 1) hi = -hi;
                    if (l0 < 4) sumi0 += lo * x->qs[q8_offset + j] + hi * x->qs[q8_offset + 4 + j];
                    else sumi1 += lo * x->qs[q8_offset + j] + hi * x->qs[q8_offset + 4 + j];
                }
            }
            const int sumi = (sumi0 * ls0 + sumi1 * ls1 + (sumi0 + sumi1) / 2) / 4;
            const float d = ggml_fp16_to_fp32(w->d) * ggml_fp16_to_fp32(x->d);
            lane_sum[(size_t) lane] += d * (float) sumi;
        }
    }
    for (int offset = 16; offset > 0; offset >>= 1) {
        const auto previous = lane_sum;
        for (int lane = 0; lane < 32; ++lane)
            lane_sum[(size_t) lane] = previous[(size_t) lane] + previous[(size_t) (lane ^ offset)];
    }
    return lane_sum[0];
}

// Independent scalar transcription of the CUDA IQ3_XXS/Q8_1 dot. Used only
// to inspect gate/up rows from the same captured activation as the grouped
// kernel; it does not share the production CPU mirror's implementation.
float parity_iq3_xxs_q8_1_dot(const uint8_t* row, const uint8_t* xq, int n) {
    if (n % QK_K != 0) std::abort();
    const int nb = n / QK_K;
    const auto* weights = reinterpret_cast<const block_iq3_xxs*>(row);
    const auto* acts = reinterpret_cast<const ParityQ81*>(xq);
    std::array<float, 32> lane_sum{};
    for (int lane = 0; lane < 32; ++lane) {
        for (int k = lane; k < nb * 8; k += 32) {
            const int kbx = k / 8;
            const int iqs = 2 * (k % 8);
            const auto* w = weights + kbx;
            const auto* x = acts + kbx * 8 + iqs / 2;
            uint32_t packed[2];
            std::memcpy(&packed[0], w->qs + 4 * iqs, sizeof(uint32_t));
            std::memcpy(&packed[1], w->qs + 4 * (iqs + 1), sizeof(uint32_t));
            uint8_t q3[8];
            std::memcpy(q3, packed, sizeof(q3));
            uint32_t aux32;
            std::memcpy(&aux32, w->qs + 4 * (QK_K / 16 + iqs / 2), sizeof(aux32));
            int sumi = 0;
            for (int l0 = 0; l0 < 8; l0 += 2) {
                const uint8_t raw_signs = (uint8_t) (aux32 >> (7 * l0 / 2));
                unsigned parity = 0;
                for (unsigned bits = raw_signs; bits != 0; bits &= bits - 1) parity ^= 1;
                const uint8_t signs = raw_signs ^ ((uint8_t) parity << 7);
                const uint32_t grid_l = iq3xxs_grid[q3[l0 + 0]];
                const uint32_t grid_h = iq3xxs_grid[q3[l0 + 1]];
                for (int j = 0; j < 4; ++j) {
                    int gl = (int8_t) (grid_l >> (8 * j));
                    int gh = (int8_t) (grid_h >> (8 * j));
                    if ((signs >> j) & 1) gl = -gl;
                    if ((signs >> (j + 4)) & 1) gh = -gh;
                    sumi += gl * (int) x->qs[4 * l0 + j];
                    sumi += gh * (int) x->qs[4 * (l0 + 1) + j];
                }
            }
            const int ls = (int) (aux32 >> 28);
            sumi = (ls * sumi + sumi / 2) / 2;
            const float d = ggml_fp16_to_fp32(w->d) * ggml_fp16_to_fp32(x->d);
            lane_sum[(size_t) lane] += d * (float) sumi;
        }
    }
    for (int offset = 16; offset > 0; offset >>= 1) {
        const auto previous = lane_sum;
        for (int lane = 0; lane < 32; ++lane)
            lane_sum[(size_t) lane] = previous[(size_t) lane] + previous[(size_t) (lane ^ offset)];
    }
    return lane_sum[0];
}
}  // namespace

static double rel(const std::vector<float>& a, const std::vector<float>& b) {
    double n = 0, d = 0;
    for (size_t i = 0; i < a.size(); ++i) { n += std::fabs((double) a[i] - b[i]); d += std::fabs((double) b[i]); }
    return n / (d + 1e-30);
}


namespace {
constexpr int NT = 3, E = 7;
constexpr int64_t H = 2560, FF = 640;

// Compare the actual GGML CPU Q8_1 block producer with Strata's CUDA producer
// for a captured service activation. The two implementations intentionally
// encode different `s` values: GGML stores d*sum(q), while this CUDA path stores
// the sum of the original FP32 inputs for weight formats whose dot needs it.
int check_q8_1_quantizers(const std::vector<float>& x, cudaStream_t stream) {
    if (x.size() != H) {
        std::fprintf(stderr, "Q8_1 quantizer check needs %lld activation values, got %zu\n",
                     (long long) H, x.size());
        return 1;
    }
    const size_t bytes = ggml_row_size(GGML_TYPE_Q8_1, H);
    std::vector<uint8_t> cpu_q(bytes), gpu_q(bytes), grouped_q(bytes);
    const auto* traits = ggml_get_type_traits_cpu(GGML_TYPE_Q8_1);
    if (!traits || !traits->from_float) {
        std::fprintf(stderr, "GGML CPU Q8_1 quantizer is unavailable\n");
        return 1;
    }
    traits->from_float(x.data(), cpu_q.data(), H);
    const auto cuda_check = [](cudaError_t error, const char* operation) {
        if (error != cudaSuccess) {
            std::fprintf(stderr, "Q8_1 quantizer check: %s: %s\n", operation, cudaGetErrorString(error));
            std::exit(1);
        }
    };
    float* dx = nullptr;
    void* dq = nullptr;
    cuda_check(cudaMalloc(&dx, x.size() * sizeof(float)), "cudaMalloc input");
    cuda_check(cudaMalloc(&dq, bytes), "cudaMalloc Q8_1 blocks");
    cuda_check(cudaMemcpy(dx, x.data(), x.size() * sizeof(float), cudaMemcpyHostToDevice), "copy input");
    strata::kernels::native_quantize_q8_1(dx, dq, (int) H, 1, stream);
    cuda_check(cudaGetLastError(), "launch CUDA quantizer");
    cuda_check(cudaStreamSynchronize(stream), "synchronize CUDA quantizer");
    cuda_check(cudaMemcpy(gpu_q.data(), dq, bytes, cudaMemcpyDeviceToHost), "copy Q8_1 blocks");
    strata::kernels::quantize_q8_1_rows(dx, 1, H, dq, stream);
    cuda_check(cudaGetLastError(), "launch grouped-row CUDA quantizer");
    cuda_check(cudaStreamSynchronize(stream), "synchronize grouped-row CUDA quantizer");
    cuda_check(cudaMemcpy(grouped_q.data(), dq, bytes, cudaMemcpyDeviceToHost), "copy grouped-row Q8_1 blocks");
    cuda_check(cudaFree(dq), "free Q8_1 blocks");
    cuda_check(cudaFree(dx), "free input");

    size_t scale_mismatches = 0, code_mismatches = 0, sum_mismatches = 0;
    size_t oracle_scale_mismatches = 0, oracle_cpu_code_errors = 0;
    size_t oracle_gpu_code_errors = 0, oracle_gpu_code_one_step = 0;
    size_t oracle_cpu_sum_mismatches = 0, oracle_gpu_sum_mismatches = 0;
    int first_oracle_failure = -1;
    int first_bad_code = -1, first_actual_code = 0, first_cpu_formula_code = 0, first_gpu_formula_code = 0;
    uint16_t first_cpu_sum = 0, first_gpu_sum = 0, first_expected_cpu_sum = 0, first_expected_gpu_sum = 0;
    size_t grouped_cpu_code_mismatches = 0, grouped_native_code_mismatches = 0;
    int first_grouped_cpu_code_mismatch = -1;
    for (int block = 0; block < H / 32; ++block) {
        const uint8_t* c = cpu_q.data() + (size_t) block * 36;
        const uint8_t* g = gpu_q.data() + (size_t) block * 36;
        const uint8_t* gr = grouped_q.data() + (size_t) block * 36;
        for (int i = 0; i < 32; ++i) {
            const bool cpu_diff = c[4 + i] != gr[4 + i];
            grouped_cpu_code_mismatches += cpu_diff;
            grouped_native_code_mismatches += g[4 + i] != gr[4 + i];
            if (cpu_diff && first_grouped_cpu_code_mismatch < 0)
                first_grouped_cpu_code_mismatch = 32 * block + i;
        }
        scale_mismatches += std::memcmp(c, g, 2) != 0;
        sum_mismatches += std::memcmp(c + 2, g + 2, 2) != 0;
        code_mismatches += std::memcmp(c + 4, g + 4, 32) != 0;

        float amax = 0.f;
        const float* row = x.data() + (size_t) block * 32;
        for (int i = 0; i < 32; ++i) {
            amax = std::max(amax, std::fabs(row[i]));
        }
        std::array<float, 32> sums{};
        std::copy(row, row + 32, sums.begin());
        // Independent host transcription of the CUDA warp XOR-sum order.
        for (int offset = 16; offset > 0; offset >>= 1) {
            const auto prior = sums;
            for (int lane = 0; lane < 32; ++lane) sums[lane] = prior[lane] + prior[lane ^ offset];
        }
        const float d = amax / 127.f;
        const float inv = d > 0.f ? 1.f / d : 0.f;
        int cpu_qsum = 0;
        bool cpu_codes_ok = true, gpu_codes_ok = true;
        bool gpu_code_one_step = false;
        for (int i = 0; i < 32; ++i) {
            // Orin's GGML NEON quantizer uses vcvtn (ties to even), unlike the
            // scalar reference's roundf (ties away from zero).
            const int cpu_q = std::clamp((int) std::nearbyint(row[i] * inv), -127, 127);
            const int gpu_q = std::clamp((int) std::round(row[i] / d), -127, 127);
            cpu_qsum += cpu_q;
            cpu_codes_ok &= c[4 + i] == (uint8_t) (int8_t) cpu_q;
            const int gpu_actual = (int8_t) g[4 + i];
            const int gpu_step = std::abs(gpu_actual - gpu_q);
            gpu_codes_ok &= gpu_step <= 1;
            gpu_code_one_step |= gpu_step == 1;
            if (first_bad_code < 0 && (c[4 + i] != (uint8_t) (int8_t) cpu_q ||
                                       std::abs(gpu_actual - gpu_q) > 1)) {
                first_bad_code = i;
                first_actual_code = (int8_t) c[4 + i];
                first_cpu_formula_code = cpu_q;
                first_gpu_formula_code = gpu_q;
            }
        }
        const ggml_fp16_t half_d = ggml_fp32_to_fp16(d);
        const ggml_fp16_t cpu_sum = ggml_fp32_to_fp16(d * (float) cpu_qsum);
        const ggml_fp16_t gpu_sum = ggml_fp32_to_fp16(sums[0]);
        const bool scale_ok = std::memcmp(c, &half_d, 2) == 0 && std::memcmp(g, &half_d, 2) == 0;
        const bool cpu_sum_ok = std::memcmp(c + 2, &cpu_sum, 2) == 0;
        const bool gpu_sum_ok = std::memcmp(g + 2, &gpu_sum, 2) == 0;
        if ((!scale_ok || !cpu_codes_ok || !gpu_codes_ok || !cpu_sum_ok || !gpu_sum_ok) && first_oracle_failure < 0) {
            first_cpu_sum = (uint16_t) c[2] | (uint16_t) c[3] << 8;
            first_gpu_sum = (uint16_t) g[2] | (uint16_t) g[3] << 8;
            first_expected_cpu_sum = cpu_sum;
            first_expected_gpu_sum = gpu_sum;
        }
        oracle_scale_mismatches += !scale_ok;
        oracle_cpu_code_errors += !cpu_codes_ok;
        oracle_gpu_code_errors += !gpu_codes_ok;
        oracle_gpu_code_one_step += gpu_code_one_step;
        oracle_cpu_sum_mismatches += !cpu_sum_ok;
        oracle_gpu_sum_mismatches += !gpu_sum_ok;
        if ((!scale_ok || !cpu_codes_ok || !gpu_codes_ok || !cpu_sum_ok || !gpu_sum_ok) && first_oracle_failure < 0) {
            first_oracle_failure = block;
        }
    }
    std::printf("captured activation Q8_1 blocks=%lld: CPU/GPU scale mismatches=%zu, code mismatches=%zu, "
                "stored-sum mismatches=%zu (GGML d*sum(q), CUDA sum(input)); independent checks: "
                "scale-errors=%zu CPU-code-errors=%zu CUDA-code-errors-over-1=%zu CUDA-code-1-step-blocks=%zu "
                "GGML-sum-errors=%zu CUDA-sum-errors=%zu first-block=%d; grouped-row CUDA code mismatches "
                "vs CPU=%zu, vs native CUDA=%zu, first CPU mismatch index=%d\n",
                (long long) (H / 32), scale_mismatches, code_mismatches, sum_mismatches,
                oracle_scale_mismatches, oracle_cpu_code_errors, oracle_gpu_code_errors,
                oracle_gpu_code_one_step, oracle_cpu_sum_mismatches, oracle_gpu_sum_mismatches,
                first_oracle_failure, grouped_cpu_code_mismatches, grouped_native_code_mismatches,
                first_grouped_cpu_code_mismatch);
    if (first_oracle_failure >= 0) {
        std::printf("first formula mismatch detail: block=%d code-index=%d actual=%d CPU-formula=%d GPU-formula=%d "
                    "CPU-sum=%04x expected=%04x GPU-sum=%04x expected=%04x\n",
                    first_oracle_failure, first_bad_code, first_actual_code, first_cpu_formula_code,
                    first_gpu_formula_code, first_cpu_sum, first_expected_cpu_sum, first_gpu_sum,
                    first_expected_gpu_sum);
    }
    return scale_mismatches || code_mismatches || oracle_scale_mismatches || oracle_cpu_code_errors ||
                   oracle_gpu_code_errors ||
                   oracle_cpu_sum_mismatches || oracle_gpu_sum_mismatches
               ? 1
               : 0;
}

int check_iq4_nl_down_q8_1(const cpu::NativeFmt& f, const std::vector<uint8_t>& blob, int seed,
                           cudaStream_t stream) {
    constexpr int N_IN = (int) FF, N_OUT = (int) H;
    const size_t qbytes = ggml_row_size(GGML_TYPE_Q8_1, N_IN);
    std::mt19937 rng(0x4e4c + seed);
    std::normal_distribution<float> normal(0.f, 1.f);
    std::vector<float> h((size_t) N_IN), cpu_y((size_t) N_OUT), gpu_y((size_t) N_OUT);
    for (float& value : h) value = normal(rng);

    std::vector<uint8_t> cpu_q(qbytes);
    cpu::NativeFmt down_fmt = f;
    down_fmt.d_act = GGML_TYPE_Q8_1;
    cpu::native_quant_h(down_fmt, h.data(), cpu_q.data());

    const auto check = [](cudaError_t error, const char* operation) {
        if (error != cudaSuccess) {
            std::fprintf(stderr, "IQ4_NL Q8_1 down parity: %s: %s\n", operation, cudaGetErrorString(error));
            std::exit(1);
        }
    };
    float* d_h = nullptr;
    void *d_q = nullptr, *d_w = nullptr;
    float* d_y = nullptr;
    const size_t down_bytes = f.d_row * (size_t) N_OUT;
    check(cudaMalloc(&d_h, h.size() * sizeof(float)), "cudaMalloc activation");
    check(cudaMalloc(&d_q, qbytes), "cudaMalloc Q8_1");
    check(cudaMalloc(&d_w, down_bytes), "cudaMalloc weights");
    check(cudaMalloc(&d_y, gpu_y.size() * sizeof(float)), "cudaMalloc output");
    check(cudaMemcpy(d_h, h.data(), h.size() * sizeof(float), cudaMemcpyHostToDevice), "copy activation");
    check(cudaMemcpy(d_w, blob.data() + f.down_off, down_bytes, cudaMemcpyHostToDevice), "copy down weights");
    strata::kernels::native_quantize_q8_1(d_h, d_q, N_IN, 1, stream);
    strata::kernels::native_mmvq(GGML_TYPE_IQ4_NL, d_w, d_q, d_y, N_IN, N_OUT, 1, stream);
    check(cudaGetLastError(), "launch CUDA IQ4_NL MMVQ");
    check(cudaStreamSynchronize(stream), "synchronize CUDA IQ4_NL MMVQ");
    check(cudaMemcpy(gpu_y.data(), d_y, gpu_y.size() * sizeof(float), cudaMemcpyDeviceToHost), "copy CUDA output");

    std::vector<uint8_t> gpu_q(qbytes);
    check(cudaMemcpy(gpu_q.data(), d_q, qbytes, cudaMemcpyDeviceToHost), "copy Q8_1 activation");
    int q8_mismatch_blocks = 0;
    for (size_t offset = 0; offset < qbytes; offset += 36) {
        // The stored sum intentionally differs; IQ4_NL consumes scale and codes only.
        q8_mismatch_blocks += std::memcmp(cpu_q.data() + offset, gpu_q.data() + offset, 2) != 0 ||
                              std::memcmp(cpu_q.data() + offset + 4, gpu_q.data() + offset + 4, 32) != 0;
    }
    const void* qptr[1] = {cpu_q.data()};
    float* yptr[1] = {cpu_y.data()};
    cpu::native_down_rows(down_fmt, blob.data(), qptr, 1, yptr, 0, N_OUT);
    size_t value_mismatches = 0;
    for (size_t i = 0; i < cpu_y.size(); ++i)
        value_mismatches += std::memcmp(&cpu_y[i], &gpu_y[i], sizeof(float)) != 0;
    std::printf("          IQ4_NL down Q8_1 standalone-MMVQ diagnostic: quantizer scale/code blocks %d/%zu differ; "
                "CPU/grouped-service vs standalone-CUDA output words %zu/%zu differ (schedule differs)\n",
                q8_mismatch_blocks, qbytes / 36, value_mismatches, cpu_y.size());

    check(cudaFree(d_y), "free output");
    check(cudaFree(d_w), "free weights");
    check(cudaFree(d_q), "free Q8_1");
    check(cudaFree(d_h), "free activation");
    // native_mmvq uses native_small_mmvq's four-warp schedule. The service's
    // grouped native_down_multi_kernel uses row_dot_multi's lane-strided
    // schedule, which q8_1_iq4_nl_cuda_dot mirrors. The full grouped expert
    // check below is the relevant arithmetic oracle; this standalone result is
    // retained only to make the schedule distinction visible. Q8_1 consumed
    // scale and code bytes must still match independently.
    return q8_mismatch_blocks == 0 ? 0 : 1;
}

// The three ways and the dequantizers for one expert blob and token-group width; returns failed checks.
template <int N>
int check_blob(const cpu::NativeFmt& f, const std::vector<uint8_t>& blob, int seed, const std::string& label,
               cudaStream_t s, const std::vector<float>* service_activation = nullptr,
               const std::string& dump_f32_dir = {}) {
    int failures = 0;
    // (a) the float reference
    const auto* tg = ggml_get_type_traits((ggml_type) f.gu_type);
    const auto* td = ggml_get_type_traits((ggml_type) f.d_type);
    std::vector<float> G((size_t) FF * H), U((size_t) FF * H), D((size_t) H * FF);
    for (int64_t r = 0; r < FF; ++r) {
        tg->to_float(blob.data() + r * f.gu_row, G.data() + r * H, H);
        tg->to_float(blob.data() + f.up_off + r * f.gu_row, U.data() + r * H, H);
    }
    for (int64_t r = 0; r < H; ++r) td->to_float(blob.data() + f.down_off + r * f.d_row, D.data() + r * FF, FF);
    std::mt19937 rng(11 + seed);
    std::normal_distribution<float> nd(0.f, 1.f);
    std::vector<float> x((size_t) N * H);
    if (service_activation != nullptr) {
        if (service_activation->size() == (size_t) H) {
            for (int k = 0; k < N; ++k)
                std::copy(service_activation->begin(), service_activation->end(), x.begin() + (size_t) k * H);
        } else if (service_activation->size() == (size_t) N * H) {
            x = *service_activation;
        } else {
            std::fprintf(stderr, "%s: service activation has %zu values; expected %lld or %lld\n", label.c_str(),
                         service_activation->size(), (long long) H, (long long) N * H);
            return 1;
        }
    } else {
        for (auto& v : x) v = nd(rng);
    }
    if (!dump_f32_dir.empty()) {
        std::string stem = label;
        std::replace(stem.begin(), stem.end(), ' ', '-');
        const auto write = [&](const std::string& suffix, const float* values, size_t count) {
            const std::string path = dump_f32_dir + "/" + stem + "-" + suffix + ".f32";
            std::ofstream out(path, std::ios::binary);
            if (!out || !out.write(reinterpret_cast<const char*>(values), (std::streamsize) (count * sizeof(float)))) {
                std::fprintf(stderr, "%s: cannot write parity dump %s\n", label.c_str(), path.c_str());
                return false;
            }
            return true;
        };
        if (!write("gate", G.data(), G.size()) || !write("up", U.data(), U.size()) ||
            !write("down", D.data(), D.size()) || !write("activation", x.data(), x.size())) return 1;
    }
    std::vector<float> ref((size_t) N * H), got_c((size_t) N * H), got_g((size_t) N * H);
    std::vector<uint8_t> cpu_hq_snapshot;
    std::vector<uint8_t> cpu_activation_snapshot;
    std::vector<float> cpu_hidden_snapshot;
    std::vector<float> cpu_gate_snapshot, cpu_up_snapshot;
    const bool compare_hidden_q8_1 = std::getenv("STRATA_PARITY_COMPARE_HIDDEN_Q8_1") != nullptr;
    for (int k = 0; k < N; ++k) {
        std::vector<float> h(FF);
        for (int64_t r = 0; r < FF; ++r) {
            double g = 0, u = 0;
            for (int64_t i = 0; i < H; ++i) { g += (double) G[r * H + i] * x[k * H + i]; u += (double) U[r * H + i] * x[k * H + i]; }
            h[r] = (float) (g / (1.0 + std::exp(-g)) * u);
        }
        for (int64_t r = 0; r < H; ++r) {
            double o = 0;
            for (int64_t i = 0; i < FF; ++i) o += (double) D[r * FF + i] * h[i];
            ref[k * H + r] = (float) o;
        }
    }
    // (b) the CPU
    {
        std::vector<std::vector<uint8_t>> act(N, std::vector<uint8_t>(cpu::kNativeActBytes));
        std::vector<std::vector<uint8_t>> hq(N, std::vector<uint8_t>(cpu::kNativeHBytes));
        std::vector<std::vector<float>> ff(N, std::vector<float>(FF));
        const void* a[N];
        float* ffp[N];
        const void* hp[N];
        float* op[N];
        for (int k = 0; k < N; ++k) {
            cpu::native_quant_act(f, x.data() + k * H, act[k].data());
            a[k] = act[k].data();
            ffp[k] = ff[k].data();
        }
        cpu::native_gu_rows(f, blob.data(), a, N, ffp, 0, (int) FF);
        if (std::getenv("STRATA_PARITY_DUMP_HIDDEN_Q8_1") != nullptr && f.d_act == GGML_TYPE_Q8_1) {
            const size_t act_bytes = ggml_row_size(GGML_TYPE_Q8_1, H);
            cpu_activation_snapshot.resize((size_t) N * act_bytes);
            for (int token = 0; token < N; ++token)
                std::memcpy(cpu_activation_snapshot.data() + (size_t) token * act_bytes, a[token], act_bytes);
        }
        if (std::getenv("STRATA_PARITY_DUMP_HIDDEN_Q8_1") != nullptr) {
            cpu_hidden_snapshot.resize((size_t) N * FF);
            for (int k = 0; k < N; ++k)
                std::copy(ff[k].begin(), ff[k].end(), cpu_hidden_snapshot.begin() + (size_t) k * FF);
            if ((f.gu_type == GGML_TYPE_IQ2_S || f.gu_type == GGML_TYPE_IQ3_XXS) &&
                f.d_act == GGML_TYPE_Q8_1) {
                cpu_gate_snapshot.resize((size_t) N * FF);
                cpu_up_snapshot.resize((size_t) N * FF);
                size_t reconstructed_differences = 0;
                const auto dot_q8_1 = f.gu_type == GGML_TYPE_IQ2_S
                    ? parity_iq2_s_q8_1_dot : parity_iq3_xxs_q8_1_dot;
                for (int token = 0; token < N; ++token) {
                    const auto* xq = static_cast<const uint8_t*>(a[token]);
                    for (int64_t row = 0; row < FF; ++row) {
                        const float g = dot_q8_1(blob.data() + row * f.gu_row, xq, (int) H);
                        const float u = dot_q8_1(blob.data() + f.up_off + row * f.gu_row, xq, (int) H);
                        const size_t at = (size_t) token * FF + (size_t) row;
                        cpu_gate_snapshot[at] = g;
                        cpu_up_snapshot[at] = u;
                        // Mirror the selected native_gu_rows operation order. The
                        // exp2f route is a distinct opt-in candidate and must not
                        // be judged against the default expf expression.
                        float h;
                        if (f.q8_1_exp2f_silu) {
                            constexpr float kLog2E = 1.4426950408889634f;
                            const float e = std::exp2((-g) * kLog2E);
                            h = (g / (1.f + e)) * u;
                        } else {
                            h = (g / (1.f + std::exp(-g))) * u;
                        }
                        reconstructed_differences += std::memcmp(&h, &cpu_hidden_snapshot[at], sizeof(float)) != 0;
                    }
                }
                std::printf("          independent %s/Q8_1 gate/up reconstruction vs native hidden: "
                            "%zu/%zu words differ\n",
                            f.gu_type == GGML_TYPE_IQ2_S ? "IQ2_S" : "IQ3_XXS",
                            reconstructed_differences, cpu_hidden_snapshot.size());
                if (reconstructed_differences != 0) ++failures;
                if (!dump_f32_dir.empty()) {
                    std::string stem = label;
                    std::replace(stem.begin(), stem.end(), ' ', '-');
                    for (const auto& item : {std::pair<const char*, const std::vector<float>*>("cpu-gate", &cpu_gate_snapshot),
                                             std::pair<const char*, const std::vector<float>*>("cpu-up", &cpu_up_snapshot)}) {
                        const std::string path = dump_f32_dir + "/" + stem + "--" + item.first + ".f32";
                        std::ofstream out(path, std::ios::binary);
                        if (!out || !out.write(reinterpret_cast<const char*>(item.second->data()),
                                               (std::streamsize) ((size_t) N * FF * 4))) {
                            std::fprintf(stderr, "%s: cannot write CPU gate/up dump %s\n", label.c_str(), path.c_str());
                            return 1;
                        }
                    }
                }
            }
        }
        // either multi-token kernel: IQ4_XS has an AVX-2 one and no AVX-512 one, so the gate cannot be
        // iq512_supported alone - that would leave the format untested on every CPU.
#if STRATA_CPU_X86
        if (cpu::iq512_supported(f.gu_type) || cpu::iq256_supported(f.gu_type)) {
            // ggml's own vec_dot, same Q8_K activations: the reference for both multi-token kernels
            // (float-order differences only)
            const auto* tc = ggml_get_type_traits_cpu((ggml_type) f.gu_type);
            std::vector<float> gref((size_t) N * FF);
            for (int k = 0; k < N; ++k)
                for (int64_t r = 0; r < FF; ++r)
                    tc->vec_dot((int) H, &gref[k * FF + r], 0, blob.data() + r * f.gu_row, 0, a[k], 0, 1);
            double usg = 0.0;
            {   // ggml single-token throughput, the weights cache-resident (compute bound)
                const int it = 50;
                auto t0 = std::chrono::steady_clock::now();
                for (int i = 0; i < it; ++i)
                    for (int64_t r = 0; r < FF; ++r) {
                        float gg, uu;
                        tc->vec_dot((int) H, &gg, 0, blob.data() + r * f.gu_row, 0, a[0], 0, 1);
                        tc->vec_dot((int) H, &uu, 0, blob.data() + f.up_off + r * f.gu_row, 0, a[0], 0, 1);
                    }
                auto t1 = std::chrono::steady_clock::now();
                usg = std::chrono::duration<double, std::micro>(t1 - t0).count() / it;
            }
            // one multi-token kernel: parity against ggml's vec_dot, then one-token and N-token throughput
            auto check = [&](const char* tag, bool is512) {
                std::vector<float> g((size_t) N * FF);
                float* gp[N];
                for (int k = 0; k < N; ++k) gp[k] = g.data() + k * FF;
                (is512 ? cpu::iq512_rows : cpu::iq256_rows)(f.gu_type, blob.data(), f.gu_row, (int) H, a, N, gp, 0, (int) FF);
                const double rg = rel(g, gref);
                std::printf("          %s %s gate rows vs ggml vec_dot: rel %.2e\n",
                            ggml_type_name((ggml_type) f.gu_type), tag, rg);
                if (rg > 1e-5) {   // ggml's own vec_dot is the reference: above 1e-5 it is a real mismatch,
                    std::printf("          %s %s gate rows MISMATCH (rel %.2e > 1e-5)\n",
                                ggml_type_name((ggml_type) f.gu_type), tag, rg);   // not rounding (measured 3e-8)
                    ++failures;
                }
                float* f1[1] = {ffp[0]};
                const int it = 50;
                const auto gu = is512 ? cpu::iq512_gu_rows : cpu::iq256_gu_rows;
                auto t0 = std::chrono::steady_clock::now();
                for (int i = 0; i < it; ++i) gu(f.gu_type, blob.data(), f.gu_row, f.up_off, (int) H, a, 1, f1, 0, (int) FF);
                auto t1 = std::chrono::steady_clock::now();
                for (int i = 0; i < it; ++i) gu(f.gu_type, blob.data(), f.gu_row, f.up_off, (int) H, a, N, ffp, 0, (int) FF);
                auto t2 = std::chrono::steady_clock::now();
                const double us1 = std::chrono::duration<double, std::micro>(t1 - t0).count() / it;
                const double usn = std::chrono::duration<double, std::micro>(t2 - t1).count() / it;
                std::printf("          gate+up one token one thread: %s %.0f us (%.2f GB/s), ggml %.0f us (%.2f GB/s)\n",
                            tag, us1, 2.0 * f.up_off / us1 / 1e3, usg, 2.0 * f.up_off / usg / 1e3);
                std::printf("          gate+up %d tokens one thread: %s %.0f us vs ggml %d x %.0f us\n", N, tag, usn, N, usg);
            };
            // guarded: the binary runs on AVX-2 CPUs too, and IQ4_XS has no AVX-512 kernel (an empty switch)
            if (cpu::cpu_avx512_ok() && cpu::iq512_supported(f.gu_type)) check("avx512", true);
            if (cpu::cpu_avx2_ok() && cpu::iq256_supported(f.gu_type)) check("avx2", false);   // no AVX2: ggml-cpu only
        }
#endif
        for (int k = 0; k < N; ++k) {
            cpu::native_quant_h(f, ff[k].data(), hq[k].data());
            hp[k] = hq[k].data();
            op[k] = got_c.data() + k * H;
            if (compare_hidden_q8_1 && f.d_act == GGML_TYPE_Q8_1) {
                const size_t row_bytes = ggml_row_size(GGML_TYPE_Q8_1, (int64_t) FF);
                cpu_hq_snapshot.insert(cpu_hq_snapshot.end(), hq[k].begin(), hq[k].begin() + row_bytes);
            }
        }
        cpu::native_down_rows(f, blob.data(), hp, N, op, 0, (int) H);
        if (!dump_f32_dir.empty()) {
            std::string stem = label;
            std::replace(stem.begin(), stem.end(), ' ', '-');
            for (const auto& item : {std::pair<const char*, const std::vector<float>*>("cpu-output", &got_c),
                                     std::pair<const char*, const std::vector<float>*>("float-output", &ref)}) {
                const std::string path = dump_f32_dir + "/" + stem + "-" + item.first + ".f32";
                std::ofstream out(path, std::ios::binary);
                if (!out || !out.write(reinterpret_cast<const char*>(item.second->data()), H * sizeof(float))) {
                    std::fprintf(stderr, "%s: cannot write parity dump %s\n", label.c_str(), path.c_str());
                    return 1;
                }
            }
        }
        {   // #152: a token's rows must not depend on how many tokens share the call - each token alone (nt = 1)
            // against its row of the N-token call above, bit for bit, gate/up and down
            size_t gu_diff = 0, dn_diff = 0;
            std::vector<float> one_ff(FF), one_out(H);
            std::vector<uint8_t> one_h(ggml_row_size((ggml_type) f.d_act, FF));
            // the N-token gate/up rows again: the throughput loops above overwrote ff with other kernels' rows
            for (int k = 0; k < N; ++k) ffp[k] = ff[k].data();
            cpu::native_gu_rows(f, blob.data(), a, N, ffp, 0, (int) FF);
            for (int k = 0; k < N; ++k) {
                const void* a1[1] = {a[k]};
                float* f1[1] = {one_ff.data()};
                cpu::native_gu_rows(f, blob.data(), a1, 1, f1, 0, (int) FF);
                for (int64_t r = 0; r < FF; ++r) gu_diff += std::memcmp(&one_ff[r], &ff[k][r], 4) != 0;
                cpu::native_quant_h(f, one_ff.data(), one_h.data());
                const void* h1[1] = {one_h.data()};
                float* o1[1] = {one_out.data()};
                cpu::native_down_rows(f, blob.data(), h1, 1, o1, 0, (int) H);
                for (int64_t r = 0; r < H; ++r) dn_diff += std::memcmp(&one_out[r], &got_c[k * H + r], 4) != 0;
                if (k == 0 && !dump_f32_dir.empty()) {
                    std::string stem = label;
                    std::replace(stem.begin(), stem.end(), ' ', '-');
                    const std::string path = dump_f32_dir + "/" + stem + "-cpu-output-nt1.f32";
                    std::ofstream out(path, std::ios::binary);
                    if (!out || !out.write(reinterpret_cast<const char*>(one_out.data()), H * sizeof(float))) {
                        std::fprintf(stderr, "%s: cannot write single-token parity dump %s\n",
                                     label.c_str(), path.c_str());
                        return 1;
                    }
                }
            }
            std::printf("          width invariance (1 vs %d tokens): gate/up %zu, down %zu rows differ\n", N,
                        gu_diff, dn_diff);
            if (gu_diff || dn_diff) ++failures;
        }
        // UD-Q4_K_XL's formats: the multi-token AVX2 kernels (kq_avx2.cpp) against ggml-cpu's vec_dot per token,
        // BIT FOR BIT, for 1..8 tokens; then the time of 4 tokens (a verify window) both ways
#if STRATA_CPU_X86
        for (int role = 0; role < 2; ++role) {
            const int type = role == 0 ? f.gu_type : f.d_type;
            if (!cpu::cpu_avx2_ok() || !cpu::kq256_supported(type) || (role == 0 && type != 12)) continue;
            const int n = role == 0 ? (int) H : (int) FF, rows = role == 0 ? (int) FF : (int) H;
            const size_t rb = role == 0 ? f.gu_row : f.d_row;
            const uint8_t* w = blob.data() + (role == 0 ? 0 : f.down_off);
            const auto* tc = ggml_get_type_traits_cpu((ggml_type) type);
            const ggml_type at = tc->vec_dot_type;
            std::vector<std::vector<uint8_t>> acts(8, std::vector<uint8_t>(ggml_row_size(at, n)));
            std::mt19937 arng(77 + seed);
            std::normal_distribution<float> and_(0.f, 1.f);
            std::vector<float> xs((size_t) n);
            const void* ap[8];
            for (int t = 0; t < 8; ++t) {
                for (auto& v : xs) v = and_(arng);
                ggml_get_type_traits_cpu(at)->from_float(xs.data(), acts[t].data(), n);
                ap[t] = acts[t].data();
            }
            std::vector<float> ref((size_t) 8 * rows), got((size_t) 8 * rows);
            for (int t = 0; t < 8; ++t)
                for (int r = 0; r < rows; ++r) tc->vec_dot(n, &ref[(size_t) t * rows + r], 0, w + (size_t) r * rb, 0, ap[t], 0, 1);
            size_t differ = 0;
            for (int nt = 1; nt <= 8; ++nt) {
                float* op[8];
                for (int t = 0; t < nt; ++t) op[t] = got.data() + (size_t) t * rows;
                cpu::kq256_rows(type, w, rb, n, ap, nt, op, 0, rows);
                for (int t = 0; t < nt; ++t)
                    differ += std::memcmp(op[t], ref.data() + (size_t) t * rows, (size_t) rows * 4) != 0;
            }
            const int it = 30;
            float* op4[4] = {got.data(), got.data() + rows, got.data() + 2 * rows, got.data() + 3 * rows};
            auto t0 = std::chrono::steady_clock::now();
            for (int i = 0; i < it; ++i) cpu::kq256_rows(type, w, rb, n, ap, 4, op4, 0, rows);
            auto t1 = std::chrono::steady_clock::now();
            for (int i = 0; i < it; ++i)
                for (int r = 0; r < rows; ++r)
                    for (int t = 0; t < 4; ++t) tc->vec_dot(n, op4[t] + r, 0, w + (size_t) r * rb, 0, ap[t], 0, 1);
            auto t2 = std::chrono::steady_clock::now();
            const double us_k = std::chrono::duration<double, std::micro>(t1 - t0).count() / it;
            const double us_g = std::chrono::duration<double, std::micro>(t2 - t1).count() / it;
            std::printf("          %s %s rows, AVX2 multi-token vs ggml vec_dot: %zu of 36 token-sets differ in any bit; "
                        "4 tokens one thread %.0f us vs ggml %.0f us (%.2fx)\n", ggml_type_name((ggml_type) type),
                        role == 0 ? "gate" : "down", differ, us_k, us_g, us_g / us_k);
            if (differ) ++failures;
        }
#endif
        if (cpu::q2_native_kernels(f.d_type)) {
            // (b2) the GGUF-layout Q2_0 kernel the pool uses for Q2_0 down projections - the AVX-512 one
            // where the CPU has it, the AVX-2 one (q2_avx2.cpp) where it does not.  Calling the AVX-512
            // kernel unconditionally faults on a Zen 2/3 CPU.
            std::vector<cpu::ActQ> a2(N);
            const cpu::ActQ* ap[N];
            std::vector<float> alt((size_t) N * H);
            float* altp[N];
            for (int k = 0; k < N; ++k) {
                cpu::act_quant_any(ff[k].data(), (int) FF, a2[k]);   // gated: AVX-512 or AVX-2 per CPU
                ap[k] = &a2[k];
                altp[k] = alt.data() + k * H;
            }
            cpu::q2_rows_any(blob.data() + f.down_off, f.d_row, (int) (FF / 64), ap, N, altp, 0, (int) H);
            std::printf("          q2_0 %s down vs ggml down: rel %.2e\n",
                        cpu::cpu_avx512_ok() ? "AVX-512" : "AVX-2", rel(alt, got_c));
        }
#if STRATA_CPU_X86
        if (f.d_type == 20 && cpu::cpu_avx2_ok()) {
            // (b3) the IQ4_NL multi-token AVX-2 kernel the pool now uses for IQ4_NL down projections,
            // against ggml-cpu's single-token vec_dot on the SAME Q8_0 activations (h), plus timing.
            std::vector<float> alt((size_t) N * H), refd((size_t) N * H);
            float* altp[N];
            for (int k = 0; k < N; ++k) altp[k] = alt.data() + k * H;
            cpu::iq4nl256_down_rows(blob.data() + f.down_off, f.d_row, (int) FF, hp, N, altp, 0, (int) H);
            const auto* tdc = ggml_get_type_traits_cpu((ggml_type) f.d_type);
            for (int k = 0; k < N; ++k)
                for (int64_t r = 0; r < H; ++r)
                    tdc->vec_dot((int) FF, refd.data() + k * H + r, 0,
                                 blob.data() + f.down_off + (size_t) r * f.d_row, 0, hp[k], 0, 1);
            const double rdn = rel(alt, refd);
            std::printf("          iq4_nl AVX-2 multi-token down vs ggml down: rel %.2e\n", rdn);
            if (rdn > 1e-5) {   // measured 1e-7; same reasoning as the gate/up rows above
                std::printf("          iq4_nl down MISMATCH (rel %.2e > 1e-5)\n", rdn);
                ++failures;
            }
            const int it = 50;
            const auto t0 = std::chrono::steady_clock::now();
            for (int i = 0; i < it; ++i)
                cpu::iq4nl256_down_rows(blob.data() + f.down_off, f.d_row, (int) FF, hp, N, altp, 0, (int) H);
            const auto t1 = std::chrono::steady_clock::now();
            for (int i = 0; i < it; ++i)
                for (int k = 0; k < N; ++k)
                    for (int64_t r = 0; r < H; ++r)
                        tdc->vec_dot((int) FF, refd.data() + k * H + r, 0,
                                    blob.data() + f.down_off + (size_t) r * f.d_row, 0, hp[k], 0, 1);
            const auto t2 = std::chrono::steady_clock::now();
            const double usn = std::chrono::duration<double, std::micro>(t1 - t0).count() / it;
            const double usg = std::chrono::duration<double, std::micro>(t2 - t1).count() / it;
            std::printf("          down %d tokens one thread: avx2 %.0f us (%.2f GB/s) vs ggml %.0f us (%.2f GB/s)\n",
                        N, usn, (double) (f.bytes - f.down_off) / usn / 1e3, usg,
                        (double) (f.bytes - f.down_off) / usg / 1e3);
        }
#endif
    }
    // (c) the GPU: one group holding the N entries
    {
        const auto L = strata::kernels::native_expert_layout(f.gu_type, f.d_type, H, FF);
        void *dblob, *dx, *dxq, *dscr;
        float* dout;
        unsigned long long* dptr;
        int32_t *dstart, *dn, *ddst, *dtok;
        cudaMalloc(&dblob, blob.size());
        cudaMalloc(&dx, x.size() * 4);
        cudaMalloc(&dxq, (size_t) N * H / 32 * 36);
        cudaMalloc(&dscr, strata::kernels::native_expert_scratch_bytes(N, FF));
        cudaMalloc((void**) &dout, (size_t) N * H * 4);
        cudaMalloc((void**) &dptr, 8);
        cudaMalloc((void**) &dstart, 8);
        cudaMalloc((void**) &dn, 4);
        cudaMalloc((void**) &ddst, N * 4);
        cudaMalloc((void**) &dtok, N * 4);
        cudaMemcpy(dblob, blob.data(), blob.size(), cudaMemcpyHostToDevice);
        cudaMemcpy(dx, x.data(), x.size() * 4, cudaMemcpyHostToDevice);
        const unsigned long long p = (unsigned long long) dblob;
        const int32_t st[2] = {0, N}, one = 1;
        std::array<int32_t, N> idx{};
        for (int token = 0; token < N; ++token) idx[(size_t) token] = token;
        cudaMemcpy(dptr, &p, 8, cudaMemcpyHostToDevice);
        cudaMemcpy(dstart, st, 8, cudaMemcpyHostToDevice);
        cudaMemcpy(dn, &one, 4, cudaMemcpyHostToDevice);
        cudaMemcpy(ddst, idx.data(), N * 4, cudaMemcpyHostToDevice);
        cudaMemcpy(dtok, idx.data(), N * 4, cudaMemcpyHostToDevice);
        strata::kernels::quantize_q8_1_rows((const float*) dx, N, H, dxq, s);
        strata::kernels::native_expert_grouped(L, dptr, dstart, dn, ddst, dtok, 1, N, dxq, dscr, dout, s);
        cudaStreamSynchronize(s);
        cudaMemcpy(got_g.data(), dout, got_g.size() * 4, cudaMemcpyDeviceToHost);
        if (compare_hidden_q8_1) {
            if (f.d_act != GGML_TYPE_Q8_1) {
                std::fprintf(stderr, "%s: hidden Q8_1 comparison requires Q8_1 down activations\n", label.c_str());
                ++failures;
            } else {
                const size_t row_bytes = ggml_row_size(GGML_TYPE_Q8_1, (int64_t) FF);
                const size_t nbytes = (size_t) N * row_bytes;
                const size_t fbytes = (size_t) N * (size_t) FF * sizeof(float);
                const size_t fa = (fbytes + 255) & ~(size_t) 255;
                const size_t hq_offset = 3 * fa;
                std::vector<uint8_t> gpu_hq(nbytes);
                if (cpu_hq_snapshot.size() != nbytes) {
                    std::fprintf(stderr, "%s: CPU hidden Q8_1 snapshot size %zu, expected %zu\n",
                                 label.c_str(), cpu_hq_snapshot.size(), nbytes);
                    ++failures;
                } else {
                    cudaMemcpy(gpu_hq.data(), (const uint8_t*) dscr + hq_offset, nbytes, cudaMemcpyDeviceToHost);
                    if (std::getenv("STRATA_PARITY_DUMP_HIDDEN_Q8_1") != nullptr && !dump_f32_dir.empty()) {
                        std::vector<float> gpu_gate((size_t) N * FF), gpu_up((size_t) N * FF);
                        std::vector<float> gpu_hidden((size_t) N * FF);
                        std::vector<uint8_t> gpu_activation((size_t) N * ggml_row_size(GGML_TYPE_Q8_1, H));
                        cudaMemcpy(gpu_gate.data(), dscr, fbytes, cudaMemcpyDeviceToHost);
                        cudaMemcpy(gpu_up.data(), (const uint8_t*) dscr + fa, fbytes, cudaMemcpyDeviceToHost);
                        cudaMemcpy(gpu_hidden.data(), (const uint8_t*) dscr + 2 * fa, fbytes, cudaMemcpyDeviceToHost);
                        cudaMemcpy(gpu_activation.data(), dxq, gpu_activation.size(), cudaMemcpyDeviceToHost);
                        std::vector<float> cpu_gate_gpuq((size_t) N * FF), cpu_up_gpuq((size_t) N * FF);
                        std::vector<float> cpu_hidden_gpuq((size_t) N * FF);
                        const bool scalar_q8_pair =
                            (f.gu_type == GGML_TYPE_IQ2_S || f.gu_type == GGML_TYPE_IQ3_XXS) &&
                            f.d_act == GGML_TYPE_Q8_1;
                        const char* exp_mode_env = std::getenv("STRATA_EXP_MODE");
                        const bool cuda_gate_up_stages_captured =
                            exp_mode_env != nullptr && std::atoi(exp_mode_env) == 0;
                        const auto dot_q8_1 = f.gu_type == GGML_TYPE_IQ2_S
                            ? parity_iq2_s_q8_1_dot : parity_iq3_xxs_q8_1_dot;
                        const size_t input_row_bytes = ggml_row_size(GGML_TYPE_Q8_1, H);
                        for (int token = 0; scalar_q8_pair && token < N; ++token) {
                            const uint8_t* xq = gpu_activation.data() + (size_t) token * input_row_bytes;
                            for (int64_t row = 0; row < FF; ++row) {
                                const float g = dot_q8_1(blob.data() + row * f.gu_row, xq, (int) H);
                                const float u = dot_q8_1(blob.data() + f.up_off + row * f.gu_row, xq, (int) H);
                                const size_t at = (size_t) token * FF + (size_t) row;
                                cpu_gate_gpuq[at] = g;
                                cpu_up_gpuq[at] = u;
                                const float sigmoid = 1.f / (1.f + std::exp(-g));
                                cpu_hidden_gpuq[at] = (g * sigmoid) * u;
                            }
                        }
                        std::string stem = label;
                        std::replace(stem.begin(), stem.end(), ' ', '-');
                        const auto write_dump = [&](const std::string& suffix, const void* values, size_t bytes) {
                            const std::string path = dump_f32_dir + "/" + stem + "-" + suffix;
                            std::ofstream out(path, std::ios::binary);
                            if (!out || !out.write(reinterpret_cast<const char*>(values), (std::streamsize) bytes)) {
                                std::fprintf(stderr, "%s: cannot write hidden-stage dump %s\n", label.c_str(), path.c_str());
                                return false;
                            }
                            return true;
                        };
                        if (cpu_hidden_snapshot.size() != (size_t) N * FF ||
                            cpu_activation_snapshot.size() != gpu_activation.size() ||
                            !write_dump("-gpu-hidden.f32", gpu_hidden.data(), fbytes) ||
                            !write_dump("-cpu-hidden-on-gpu-activation.f32", cpu_hidden_gpuq.data(), fbytes) ||
                            !write_dump("-cpu-activation.q8_1", cpu_activation_snapshot.data(),
                                        cpu_activation_snapshot.size()) ||
                            !write_dump("-gpu-activation.q8_1", gpu_activation.data(), gpu_activation.size()) ||
                            !write_dump("-cpu-hidden.f32", cpu_hidden_snapshot.data(), fbytes) ||
                            !write_dump("-cpu-hidden.q8_1", cpu_hq_snapshot.data(), nbytes) ||
                            !write_dump("-gpu-hidden.q8_1", gpu_hq.data(), nbytes)) return 1;
                        if (scalar_q8_pair && !write_dump("-cpu-gate-on-gpu-activation.f32",
                                                          cpu_gate_gpuq.data(), fbytes)) return 1;
                        if (scalar_q8_pair && !write_dump("-cpu-up-on-gpu-activation.f32",
                                                          cpu_up_gpuq.data(), fbytes)) return 1;
                        if (scalar_q8_pair && cuda_gate_up_stages_captured &&
                            (!write_dump("-gpu-gate.f32", gpu_gate.data(), fbytes) ||
                             !write_dump("-gpu-up.f32", gpu_up.data(), fbytes))) return 1;
                        if (scalar_q8_pair && cuda_gate_up_stages_captured) {
                            const auto stage_diff = [](const std::vector<float>& cpu_values,
                                                       const std::vector<float>& gpu_values,
                                                       float& max_abs, double& relative_l2) {
                                size_t different = 0;
                                double sum_sq = 0.0, ref_sq = 0.0;
                                max_abs = 0.f;
                                for (size_t i = 0; i < cpu_values.size(); ++i) {
                                    const float delta = cpu_values[i] - gpu_values[i];
                                    different += std::memcmp(&cpu_values[i], &gpu_values[i], sizeof(float)) != 0;
                                    max_abs = std::max(max_abs, std::fabs(delta));
                                    sum_sq += (double) delta * delta;
                                    ref_sq += (double) gpu_values[i] * gpu_values[i];
                                }
                                relative_l2 = std::sqrt(sum_sq / (ref_sq + 1e-300));
                                return different;
                            };
                            float gate_max = 0.f, up_max = 0.f;
                            double gate_l2 = 0.0, up_l2 = 0.0;
                            const size_t gate_diffs = stage_diff(cpu_gate_gpuq, gpu_gate, gate_max, gate_l2);
                            const size_t up_diffs = stage_diff(cpu_up_gpuq, gpu_up, up_max, up_l2);
                            std::printf("          independent %s/Q8_1 gate/up dots vs CUDA stages: "
                                        "gate %zu/%zu (max %.3g, relL2 %.3g), "
                                        "up %zu/%zu (max %.3g, relL2 %.3g)\n",
                                        f.gu_type == GGML_TYPE_IQ2_S ? "IQ2_S" : "IQ3_XXS",
                                        gate_diffs, cpu_gate_gpuq.size(), gate_max, gate_l2,
                                        up_diffs, cpu_up_gpuq.size(), up_max, up_l2);

                            // Offline oracle for the host exp2f SiLU hypothesis.
                            // It consumes CUDA gate/up rows and never serves requests.
                            if (std::getenv("STRATA_PARITY_TRY_EXP2F_SILU") != nullptr &&
                                f.d_type == GGML_TYPE_IQ4_NL) {
                                constexpr float kLog2E = 1.4426950408889634f;
                                std::vector<float> candidate_hidden((size_t) N * FF);
                                std::vector<std::vector<uint8_t>> candidate_hq(
                                    (size_t) N, std::vector<uint8_t>(f.h_bytes));
                                const void* candidate_hq_rows[N];
                                std::vector<float> candidate_down((size_t) N * H);
                                float* candidate_down_rows[N];
                                for (int token = 0; token < N; ++token) {
                                    for (int64_t row = 0; row < FF; ++row) {
                                        const size_t at = (size_t) token * FF + (size_t) row;
                                        const float g = gpu_gate[at];
                                        const float u = gpu_up[at];
                                        const float e = std::exp2((-g) * kLog2E);
                                        candidate_hidden[at] = (g / (1.f + e)) * u;
                                    }
                                    cpu::native_quant_h(f, candidate_hidden.data() + (size_t) token * FF,
                                                        candidate_hq[(size_t) token].data());
                                    candidate_hq_rows[token] = candidate_hq[(size_t) token].data();
                                    candidate_down_rows[token] = candidate_down.data() + (size_t) token * H;
                                }
                                cpu::native_down_rows(f, blob.data(), candidate_hq_rows, N,
                                                      candidate_down_rows, 0, (int) H);
                                const size_t blocks_per_token = f.h_bytes / 36;
                                size_t candidate_q8_blocks_differ = 0, candidate_output_words_differ = 0;
                                double candidate_sum_sq = 0.0, candidate_ref_sq = 0.0;
                                float candidate_max_abs = 0.f;
                                for (int token = 0; token < N; ++token)
                                    for (size_t b = 0; b < blocks_per_token; ++b)
                                        candidate_q8_blocks_differ += std::memcmp(
                                            candidate_hq[(size_t) token].data() + b * 36,
                                            gpu_hq.data() + (size_t) token * f.h_bytes + b * 36, 36) != 0;
                                for (size_t i = 0; i < candidate_down.size(); ++i) {
                                    const float delta = candidate_down[i] - got_g[i];
                                    candidate_output_words_differ +=
                                        std::memcmp(&candidate_down[i], &got_g[i], sizeof(float)) != 0;
                                    candidate_max_abs = std::max(candidate_max_abs, std::fabs(delta));
                                    candidate_sum_sq += (double) delta * delta;
                                    candidate_ref_sq += (double) got_g[i] * got_g[i];
                                }
                                std::printf("          host exp2f SiLU-Q8_1 candidate: %zu/%zu hidden blocks differ; "
                                            "CPU down vs CUDA %zu/%zu words differ (max %.3g, relL2 %.3g)\n",
                                            candidate_q8_blocks_differ, blocks_per_token * (size_t) N,
                                            candidate_output_words_differ, candidate_down.size(), candidate_max_abs,
                                            std::sqrt(candidate_sum_sq / (candidate_ref_sq + 1e-300)));
                            }
                        }
                    }
                    const size_t blocks = nbytes / 36;
                    size_t blocks_differ = 0, d_bytes_differ = 0, sum_bytes_differ = 0, code_bytes_differ = 0;
                    for (size_t b = 0; b < blocks; ++b) {
                        const uint8_t* c = cpu_hq_snapshot.data() + b * 36;
                        const uint8_t* g = gpu_hq.data() + b * 36;
                        blocks_differ += std::memcmp(c, g, 36) != 0;
                        for (size_t j = 0; j < 2; ++j) d_bytes_differ += c[j] != g[j];
                        for (size_t j = 2; j < 4; ++j) sum_bytes_differ += c[j] != g[j];
                        for (size_t j = 4; j < 36; ++j) code_bytes_differ += c[j] != g[j];
                    }
                    std::printf("          CPU vs CUDA hidden Q8_1 after SwiGLU: %zu/%zu blocks differ, "
                                "%zu d-scale bytes, %zu sum-scale bytes and %zu code bytes differ\n",
                                blocks_differ, blocks, d_bytes_differ, sum_bytes_differ, code_bytes_differ);
                    std::vector<float> cpu_down_from_gpu_hq((size_t) N * H);
                    const void* gpu_hq_rows[N];
                    float* cpu_down_rows[N];
                    for (int k = 0; k < N; ++k) {
                        gpu_hq_rows[k] = gpu_hq.data() + (size_t) k * row_bytes;
                        cpu_down_rows[k] = cpu_down_from_gpu_hq.data() + (size_t) k * H;
                    }
                    cpu::native_down_rows(f, blob.data(), gpu_hq_rows, N, cpu_down_rows, 0, (int) H);
                    size_t down_words_differ = 0;
                    for (size_t i = 0; i < cpu_down_from_gpu_hq.size(); ++i)
                        down_words_differ += std::memcmp(&cpu_down_from_gpu_hq[i], &got_g[i], sizeof(float)) != 0;
                    std::printf("          CPU IQ4_NL down on CUDA hidden Q8_1 vs grouped CUDA output: "
                                "%zu/%zu words differ\n", down_words_differ, cpu_down_from_gpu_hq.size());
                    if (down_words_differ != 0) ++failures;

                }
            }
        }
        // Opt-in compatibility probe for a scalar CPU Q8_1 dot on the real native
        // IQ2_S/Q2_0 expert pair. This deliberately uses ggml's independent float
        // dequantizers for weights and Q8_1's packed codes/scales; it is an oracle,
        // not a candidate optimized CPU kernel or a serving route.
        if (std::getenv("STRATA_DIAG_CPU_Q8_1_DOT") != nullptr &&
            f.gu_type == GGML_TYPE_IQ2_S && f.d_type == GGML_TYPE_Q2_0) {
            const auto* q8_traits = ggml_get_type_traits_cpu(GGML_TYPE_Q8_1);
            if (!q8_traits || !q8_traits->from_float) {
                std::fprintf(stderr, "%s: GGML CPU Q8_1 quantizer unavailable\n", label.c_str());
                ++failures;
            } else {
                struct Q81 { ggml_fp16_t d, s; int8_t qs[32]; };
                static_assert(sizeof(Q81) == 36, "GGML Q8_1 packed layout");
                const auto quant_row = [&](const float* in, int n) {
                    std::vector<uint8_t> q(ggml_row_size(GGML_TYPE_Q8_1, n));
                    q8_traits->from_float(in, q.data(), n);
                    return q;
                };
                const auto dot_q8_1 = [](const float* w, const uint8_t* q, int n) {
                    double acc = 0.0;
                    for (int off = 0; off < n; off += 32) {
                        Q81 b{};
                        std::memcpy(&b, q + (size_t) (off / 32) * sizeof(Q81), sizeof(Q81));
                        const float d = ggml_fp16_to_fp32(b.d);
                        for (int j = 0; j < 32; ++j) acc += (double) w[off + j] * d * b.qs[j];
                    }
                    return (float) acc;
                };
                std::vector<float> candidate((size_t) N * H);
                for (int t = 0; t < N; ++t) {
                    const auto xq = quant_row(x.data() + (size_t) t * H, (int) H);
                    std::vector<float> h((size_t) FF);
                    for (int64_t r = 0; r < FF; ++r) {
                        const float g = dot_q8_1(G.data() + (size_t) r * H, xq.data(), (int) H);
                        const float u = dot_q8_1(U.data() + (size_t) r * H, xq.data(), (int) H);
                        h[(size_t) r] = (g / (1.f + std::exp(-g))) * u;
                    }
                    const auto hq = quant_row(h.data(), (int) FF);
                    for (int64_t r = 0; r < H; ++r)
                        candidate[(size_t) t * H + r] = dot_q8_1(D.data() + (size_t) r * FF, hq.data(), (int) FF);
                }
                const double e = rel(candidate, got_g);
                double max_abs = 0.0;
                size_t bitwise_diffs = 0;
                for (size_t i = 0; i < candidate.size(); ++i) {
                    max_abs = std::max(max_abs, std::fabs((double) candidate[i] - got_g[i]));
                    bitwise_diffs += std::memcmp(&candidate[i], &got_g[i], sizeof(float)) != 0;
                }
                std::printf("          scalar CPU Q8_1 dequantized-weight oracle vs CUDA: rel-L1 %.3e, max-abs %.3e, "
                            "%zu/%zu output words differ bitwise (diagnostic only)\n",
                            e, max_abs, bitwise_diffs, candidate.size());
            }
        }
        if (!dump_f32_dir.empty()) {
            std::string stem = label;
            std::replace(stem.begin(), stem.end(), ' ', '-');
            const std::string path = dump_f32_dir + "/" + stem + "-gpu-output.f32";
            std::ofstream out(path, std::ios::binary);
            if (!out || !out.write(reinterpret_cast<const char*>(got_g.data()), H * sizeof(float))) {
                std::fprintf(stderr, "%s: cannot write parity dump %s\n", label.c_str(), path.c_str());
                return 1;
            }
        }
        {   // the kernels that decode a weight part once for the N entries, bitwise vs the per-entry ones (#242;
            // the formats without a decode-once split take the per-entry kernels either way)
            std::vector<float> old_g(got_g.size());
            const bool was = strata::kernels::iq_old_kernels();
            strata::kernels::iq_set_old_kernels(!was);
            strata::kernels::native_expert_grouped(L, dptr, dstart, dn, ddst, dtok, 1, N, dxq, dscr, dout, s);
            strata::kernels::iq_set_old_kernels(was);
            cudaStreamSynchronize(s);
            cudaMemcpy(old_g.data(), dout, old_g.size() * 4, cudaMemcpyDeviceToHost);
            const bool same = std::memcmp(old_g.data(), got_g.data(), got_g.size() * 4) == 0;
            std::printf("          gpu decode-once vs per-entry kernels: %s\n", same ? "bitwise equal" : "MISMATCH");
            if (!same) ++failures;
        }
        {   // (d) the GPU dequantizers (prompt path: iq_dequant_f32/_f16; embedding: iq_embed_rows) against to_float
            float* dq = nullptr;
            uint16_t* dh = nullptr;
            int32_t* dtk = nullptr;
            cudaMalloc((void**) &dq, (size_t) FF * H * 4);
            cudaMalloc((void**) &dh, (size_t) FF * H * 2);
            cudaMalloc((void**) &dtk, (size_t) FF * 4);
            std::vector<float> got_dq((size_t) FF * H);
            std::vector<uint16_t> got_h((size_t) FF * H);
            std::vector<int32_t> tk((size_t) FF);
            for (int64_t r = 0; r < FF; ++r) tk[(size_t) r] = (int32_t) (FF - 1 - r);   // rows in reverse order
            cudaMemcpy(dtk, tk.data(), tk.size() * 4, cudaMemcpyHostToDevice);
            double dq_err = 0.0;
            size_t differ = 0, h_differ = 0;
            const struct { const uint8_t* src; int type; const std::vector<float>* want; } mats[3] = {
                {(const uint8_t*) dblob, f.gu_type, &G}, {(const uint8_t*) dblob + f.up_off, f.gu_type, &U},
                {(const uint8_t*) dblob + f.down_off, f.d_type, &D}};
            for (const auto& m : mats) {
                strata::kernels::iq_dequant_f32(m.type, m.src, FF * H, dq, s);
                strata::kernels::iq_dequant_f16(m.type, m.src, FF * H, dh, s);
                cudaStreamSynchronize(s);
                cudaMemcpy(got_dq.data(), dq, got_dq.size() * 4, cudaMemcpyDeviceToHost);
                cudaMemcpy(got_h.data(), dh, got_h.size() * 2, cudaMemcpyDeviceToHost);
                dq_err = (std::max)(dq_err, rel(got_dq, *m.want));
                for (size_t i = 0; i < got_dq.size(); ++i) {
                    differ += std::memcmp(&got_dq[i], &(*m.want)[i], 4) != 0;
                    h_differ += got_h[i] != ggml_fp32_to_fp16(got_dq[i]);
                }
            }
            // the gate matrix as an embedding table of FF rows of H values
            strata::kernels::iq_embed_rows(f.gu_type, dblob, f.gu_row, dtk, FF, H, dq, s);
            cudaStreamSynchronize(s);
            cudaMemcpy(got_dq.data(), dq, got_dq.size() * 4, cudaMemcpyDeviceToHost);
            size_t emb_differ = 0;
            for (int64_t r = 0; r < FF; ++r)
                emb_differ += std::memcmp(got_dq.data() + r * H, G.data() + (FF - 1 - r) * H, (size_t) H * 4) != 0;
            cudaFree(dq); cudaFree(dh); cudaFree(dtk);
            std::printf("          GPU dequant vs ggml to_float: rel %.2e, %zu of %lld values differ in any bit; fp16 of "
                        "it: %zu differ; embedding rows: %zu of %lld differ\n", dq_err, differ, (long long) (3 * FF * H),
                        h_differ, emb_differ, (long long) FF);
            // exact where there is one product (Q8_0), a rounding at most elsewhere (fused multiply-adds)
            const bool exact = f.gu_type == 8 && f.d_type == 8;
            if (!(dq_err < 1e-6) || h_differ || (exact && (differ || emb_differ))) ++failures;
        }
        cudaFree(dblob); cudaFree(dx); cudaFree(dxq); cudaFree(dscr); cudaFree(dout); cudaFree(dptr);
        cudaFree(dstart); cudaFree(dn); cudaFree(ddst); cudaFree(dtok);
    }
    const double ec = rel(got_c, ref), eg = rel(got_g, ref), ecg = rel(got_c, got_g);
    size_t cpu_gpu_bitwise_diff = 0;
    for (size_t i = 0; i < got_c.size(); ++i)
        cpu_gpu_bitwise_diff += std::memcmp(&got_c[i], &got_g[i], sizeof(float)) != 0;
    const bool ok = ec < 3e-2 && eg < 3e-2 && std::isfinite(ec) && std::isfinite(eg);
    if (f.gu_act == GGML_TYPE_Q8_1 && f.d_act == GGML_TYPE_Q8_1 &&
        (f.gu_type == GGML_TYPE_IQ2_S || f.gu_type == GGML_TYPE_IQ3_XXS) && f.d_type == GGML_TYPE_IQ4_NL) {
        // Full expert output also includes backend-specific expf/SwiGLU rounding.
        // Isolate the changed down dot and require exact quantizer-code and output parity.
        failures += check_iq4_nl_down_q8_1(f, blob, seed, s);
    }
    std::printf("%-9s %-8s/%-7s blob %8zu  cpu rel %.2e  gpu rel %.2e  cpu-gpu %.2e (%zu/%zu words differ)  %s\n",
                label.c_str(), ggml_type_name((ggml_type) f.gu_type), ggml_type_name((ggml_type) f.d_type), f.bytes,
                ec, eg, ecg, cpu_gpu_bitwise_diff, got_c.size(), ok ? "ok" : "FAIL");
    return failures + (ok ? 0 : 1);
}

int type_of(std::string name) {
    for (auto& c : name) c = (char) std::tolower((unsigned char) c);
    for (int t = 0; t < GGML_TYPE_COUNT; ++t) {
        const char* n = ggml_type_name((ggml_type) t);
        if (n == nullptr) continue;
        std::string m(n);
        for (auto& c : m) c = (char) std::tolower((unsigned char) c);
        if (m == name) return t;
    }
    return -1;
}

int check_q8_1_selector_contract() {
    struct Pair { int gu; int down; const char* selector; };
    const Pair pairs[] = {
        {GGML_TYPE_Q2_0, GGML_TYPE_Q2_0, "q2_0/q2_0"},
        {GGML_TYPE_IQ2_S, GGML_TYPE_Q2_0, "iq2_s/q2_0"},
        {GGML_TYPE_IQ2_S, GGML_TYPE_IQ4_NL, "iq2_s/iq4_nl"},
        {GGML_TYPE_IQ3_XXS, GGML_TYPE_Q2_0, "iq3_xxs/q2_0"},
        {GGML_TYPE_IQ3_XXS, GGML_TYPE_IQ4_NL, "iq3_xxs/iq4_nl"},
        {GGML_TYPE_IQ3_S, GGML_TYPE_Q2_0, "iq3_s/q2_0"},
        {GGML_TYPE_IQ3_S, GGML_TYPE_IQ4_NL, "iq3_s/iq4_nl"},
    };
    auto set_selector = [](const char* value) {
#ifdef _WIN32
        _putenv_s("STRATA_NATIVE_CPU_Q8_1_DOT", value);
#else
        setenv("STRATA_NATIVE_CPU_Q8_1_DOT", value, 1);
#endif
    };
    auto set_env = [](const char* name, const char* value) {
#ifdef _WIN32
        _putenv_s(name, value == nullptr ? "" : value);
#else
        if (value == nullptr) unsetenv(name);
        else setenv(name, value, 1);
#endif
    };
    set_env("STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS", nullptr);
    cpu::NativeFmt baseline[std::size(pairs)];
    int failures = 0;
    set_selector("0");
    for (size_t i = 0; i < std::size(pairs); ++i) {
        std::string err;
        if (!cpu::native_fmt(pairs[i].gu, pairs[i].down, H, FF, baseline[i], err)) {
            std::fprintf(stderr, "selector baseline %s: %s\n", pairs[i].selector, err.c_str());
            ++failures;
        }
    }
    const char* selectors[] = {"1", "all", "q2_0/q2_0", "iq2_s/q2_0", "iq2_s/iq4_nl", "iq3_xxs/q2_0",
                               "iq3_xxs/iq4_nl", "iq3_s/q2_0", "iq3_s/iq4_nl"};
    for (const char* selector : selectors) {
        set_selector(selector);
        for (size_t i = 0; i < std::size(pairs); ++i) {
            cpu::NativeFmt got;
            std::string err;
            if (!cpu::native_fmt(pairs[i].gu, pairs[i].down, H, FF, got, err)) {
                std::fprintf(stderr, "selector %s on %s: %s\n", selector, pairs[i].selector, err.c_str());
                ++failures;
                continue;
            }
            const bool selected = std::strcmp(selector, "1") == 0 || std::strcmp(selector, "all") == 0 ||
                                  std::strcmp(selector, pairs[i].selector) == 0;
            const int expected_gu = selected ? GGML_TYPE_Q8_1 : baseline[i].gu_act;
            const int expected_down = selected ? GGML_TYPE_Q8_1 : baseline[i].d_act;
            if (got.gu_act != expected_gu || got.d_act != expected_down) {
                std::fprintf(stderr, "selector %s unexpectedly routes %s: got %s/%s\n", selector,
                             pairs[i].selector, ggml_type_name((ggml_type) got.gu_act),
                             ggml_type_name((ggml_type) got.d_act));
                ++failures;
            }
        }
    }
    set_selector("iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3");
    for (size_t i = 0; i < std::size(pairs); ++i) {
        for (const int layer : {1, 2, 3}) {
            cpu::NativeFmt got;
            std::string layer_err;
            if (!cpu::native_fmt(pairs[i].gu, pairs[i].down, H, FF, got, layer_err, layer)) {
                std::fprintf(stderr, "multi-selector on %s at %d: %s\n", pairs[i].selector, layer,
                             layer_err.c_str());
                ++failures;
                continue;
            }
            const bool selected = (std::strcmp(pairs[i].selector, "iq2_s/q2_0") == 0 && layer == 1) ||
                                  (std::strcmp(pairs[i].selector, "iq2_s/iq4_nl") == 0 && layer == 3);
            const int expected_gu = selected ? GGML_TYPE_Q8_1 : baseline[i].gu_act;
            const int expected_down = selected ? GGML_TYPE_Q8_1 : baseline[i].d_act;
            if (got.gu_act != expected_gu || got.d_act != expected_down) {
                std::fprintf(stderr, "multi-selector changed %s at layer %d unexpectedly\n",
                             pairs[i].selector, layer);
                ++failures;
            }
        }
    }
    set_selector("iq3_xxs/iq4_nl@layer=7");
    for (size_t i = 0; i < std::size(pairs); ++i) {
        for (const int layer : {7, 8}) {
            cpu::NativeFmt got;
            std::string layer_err;
            if (!cpu::native_fmt(pairs[i].gu, pairs[i].down, H, FF, got, layer_err, layer)) {
                std::fprintf(stderr, "layer selector on %s at %d: %s\n", pairs[i].selector, layer,
                             layer_err.c_str());
                ++failures;
                continue;
            }
            const bool selected = std::strcmp(pairs[i].selector, "iq3_xxs/iq4_nl") == 0 && layer == 7;
            const int expected_gu = selected ? GGML_TYPE_Q8_1 : baseline[i].gu_act;
            const int expected_down = selected ? GGML_TYPE_Q8_1 : baseline[i].d_act;
            if (got.gu_act != expected_gu || got.d_act != expected_down) {
                std::fprintf(stderr, "layer selector changed %s at layer %d unexpectedly\n", pairs[i].selector,
                             layer);
                ++failures;
            }
        }
    }
    set_selector("not-a-pair");
    cpu::NativeFmt invalid;
    std::string err;
    if (cpu::native_fmt(pairs[0].gu, pairs[0].down, H, FF, invalid, err) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_DOT") == std::string::npos) {
        std::fprintf(stderr, "invalid selector was not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_selector("iq2_s/q2_0@layer=1,");
    err.clear();
    if (cpu::native_fmt(pairs[0].gu, pairs[0].down, H, FF, invalid, err) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_DOT") == std::string::npos) {
        std::fprintf(stderr, "malformed selector list was not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_selector("iq3_xxs/iq4_nl@layer=x");
    err.clear();
    if (cpu::native_fmt(pairs[2].gu, pairs[2].down, H, FF, invalid, err, 7) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_DOT") == std::string::npos) {
        std::fprintf(stderr, "malformed layer selector was accepted\n");
        ++failures;
    }
    set_selector("q2_0/q2_0@layer=0");
    set_env("STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS", "88,83,90,109");
    cpu::NativeFmt filtered, filtered_other_layer, selected_expert, unselected_expert;
    err.clear();
    if (!cpu::native_fmt(GGML_TYPE_Q2_0, GGML_TYPE_Q2_0, H, FF, filtered, err, 0) ||
        !cpu::native_fmt(GGML_TYPE_Q2_0, GGML_TYPE_Q2_0, H, FF, filtered_other_layer, err, 1)) {
        std::fprintf(stderr, "expert-filter selector setup failed: %s\n", err.c_str());
        ++failures;
    } else {
        cpu::native_fmt_for_expert(filtered, 88, selected_expert);
        cpu::native_fmt_for_expert(filtered, 77, unselected_expert);
        if (filtered.q8_1_dot_expert_ids.size() != 4 || filtered.gu_act != GGML_TYPE_Q8_1 ||
            filtered_other_layer.gu_act == GGML_TYPE_Q8_1 ||
            selected_expert.gu_act != GGML_TYPE_Q8_1 || selected_expert.d_act != GGML_TYPE_Q8_1 ||
            unselected_expert.gu_act != filtered.gu_act_default ||
            unselected_expert.d_act != filtered.d_act_default ||
            !cpu::native_q8_1_dot_expert_selected(filtered, 109) ||
            cpu::native_q8_1_dot_expert_selected(filtered, 77)) {
            std::fprintf(stderr, "expert-filter selector did not isolate its layer and IDs\n");
            ++failures;
        }
    }
    set_selector("q2_0/q2_0@layer=0,q2_0/q2_0@layer=1");
    set_env("STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS", "0=83,88;1=70,74");
    cpu::NativeFmt layer0_filter, layer1_filter, layer0_other;
    err.clear();
    if (!cpu::native_fmt(GGML_TYPE_Q2_0, GGML_TYPE_Q2_0, H, FF, layer0_filter, err, 0) ||
        !cpu::native_fmt(GGML_TYPE_Q2_0, GGML_TYPE_Q2_0, H, FF, layer1_filter, err, 1) ||
        !cpu::native_fmt(GGML_TYPE_Q2_0, GGML_TYPE_Q2_0, H, FF, layer0_other, err, 2)) {
        std::fprintf(stderr, "per-layer expert-filter selector setup failed: %s\n", err.c_str());
        ++failures;
    } else {
        cpu::NativeFmt layer0_selected, layer0_unselected, layer1_selected, layer1_unselected;
        cpu::native_fmt_for_expert(layer0_filter, 83, layer0_selected);
        cpu::native_fmt_for_expert(layer0_filter, 70, layer0_unselected);
        cpu::native_fmt_for_expert(layer1_filter, 70, layer1_selected);
        cpu::native_fmt_for_expert(layer1_filter, 83, layer1_unselected);
        if (layer0_filter.q8_1_dot_expert_ids != std::vector<int>{83, 88} ||
            layer1_filter.q8_1_dot_expert_ids != std::vector<int>{70, 74} ||
            layer0_other.gu_act == GGML_TYPE_Q8_1 ||
            layer0_selected.gu_act != GGML_TYPE_Q8_1 ||
            layer0_unselected.gu_act != layer0_filter.gu_act_default ||
            layer1_selected.gu_act != GGML_TYPE_Q8_1 ||
            layer1_unselected.gu_act != layer1_filter.gu_act_default ||
            cpu::native_q8_1_dot_expert_selected(layer1_filter, 83) ||
            !cpu::native_q8_1_dot_expert_selected(layer1_filter, 74)) {
            std::fprintf(stderr, "per-layer expert-ID lists leaked across layer or expert boundaries\n");
            ++failures;
        }
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS", "0=83,88;0=70,74");
    err.clear();
    if (cpu::native_fmt(GGML_TYPE_Q2_0, GGML_TYPE_Q2_0, H, FF, invalid, err, 0) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS") == std::string::npos) {
        std::fprintf(stderr, "duplicate per-layer expert filter was not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS", "88,,109");
    err.clear();
    if (cpu::native_fmt(GGML_TYPE_Q2_0, GGML_TYPE_Q2_0, H, FF, invalid, err, 0) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS") == std::string::npos) {
        std::fprintf(stderr, "malformed expert filter was not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_DOT_EXPERTS", nullptr);
    set_selector("all");
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER", "3");
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_EXPERT", "201");
    for (size_t i = 0; i < std::size(pairs); ++i) {
        cpu::NativeFmt selected, other_layer;
        std::string selected_err, other_err;
        if (!cpu::native_fmt(pairs[i].gu, pairs[i].down, H, FF, selected, selected_err, 3) ||
            !cpu::native_fmt(pairs[i].gu, pairs[i].down, H, FF, other_layer, other_err, 4)) {
            std::fprintf(stderr, "reciprocal-SiLU selector setup failed for %s: %s / %s\n",
                         pairs[i].selector, selected_err.c_str(), other_err.c_str());
            ++failures;
            continue;
        }
        if (!selected.q8_1_reciprocal_silu || selected.q8_1_reciprocal_silu_expert != 201 ||
            other_layer.q8_1_reciprocal_silu || other_layer.q8_1_reciprocal_silu_expert != 201) {
            std::fprintf(stderr, "reciprocal-SiLU layer/expert selector mismatch for %s\n", pairs[i].selector);
            ++failures;
        }
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER", "x");
    err.clear();
    if (cpu::native_fmt(pairs[0].gu, pairs[0].down, H, FF, invalid, err, 3) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER") == std::string::npos) {
        std::fprintf(stderr, "malformed reciprocal-SiLU layer was not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER", "3");
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_EXPERT", "999999999999999999999999999999");
    err.clear();
    if (cpu::native_fmt(pairs[0].gu, pairs[0].down, H, FF, invalid, err, 3) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_EXPERT") == std::string::npos) {
        std::fprintf(stderr, "out-of-range reciprocal-SiLU expert was not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER", nullptr);
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_EXPERT", nullptr);
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER", "3");
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT", "233");
    for (size_t i = 0; i < std::size(pairs); ++i) {
        cpu::NativeFmt selected, other_layer;
        std::string selected_err, other_err;
        if (!cpu::native_fmt(pairs[i].gu, pairs[i].down, H, FF, selected, selected_err, 3) ||
            !cpu::native_fmt(pairs[i].gu, pairs[i].down, H, FF, other_layer, other_err, 4)) {
            std::fprintf(stderr, "exp2f-SiLU selector setup failed for %s: %s / %s\n",
                         pairs[i].selector, selected_err.c_str(), other_err.c_str());
            ++failures;
            continue;
        }
        if (!selected.q8_1_exp2f_silu || selected.q8_1_exp2f_silu_expert != 233 ||
            other_layer.q8_1_exp2f_silu || other_layer.q8_1_exp2f_silu_expert != 233) {
            std::fprintf(stderr, "exp2f-SiLU layer/expert selector mismatch for %s\n", pairs[i].selector);
            ++failures;
        }
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER", "x");
    err.clear();
    if (cpu::native_fmt(pairs[0].gu, pairs[0].down, H, FF, invalid, err, 3) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER") == std::string::npos) {
        std::fprintf(stderr, "malformed exp2f-SiLU layer was not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER", "3");
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT", "999999999999999999999999999999");
    err.clear();
    if (cpu::native_fmt(pairs[0].gu, pairs[0].down, H, FF, invalid, err, 3) ||
        err.find("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT") == std::string::npos) {
        std::fprintf(stderr, "out-of-range exp2f-SiLU expert was not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER", "3");
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT", "233");
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER", "3");
    err.clear();
    if (cpu::native_fmt(pairs[0].gu, pairs[0].down, H, FF, invalid, err, 3) ||
        err.find("cannot both select") == std::string::npos) {
        std::fprintf(stderr, "conflicting SiLU probes were not rejected clearly: %s\n", err.c_str());
        ++failures;
    }
    set_env("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER", nullptr);
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER", nullptr);
    set_env("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT", nullptr);
    std::printf("Q8_1 selector contract: %s (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures;
}

// Random weights (rows of different magnitudes) quantized by ggml into the blob layout.
std::vector<uint8_t> synthetic_blob(const cpu::NativeFmt& f, int seed) {
    std::vector<uint8_t> blob(f.bytes);
    std::mt19937 rng(seed);
    std::normal_distribution<float> nd(0.f, 1.f);
    auto quant = [&](int type, int64_t rows, int64_t cols, uint8_t* dst) {
        std::vector<float> w((size_t) (rows * cols));
        for (int64_t r = 0; r < rows; ++r) {
            const float scale = 0.02f * (0.5f + (float) (r % 7) / 7.0f);
            for (int64_t c = 0; c < cols; ++c) w[(size_t) (r * cols + c)] = scale * nd(rng);
        }
        const std::vector<float> imatrix((size_t) cols, 1.0f);
        ggml_quantize_chunk((ggml_type) type, w.data(), dst, 0, rows, cols,
                            ggml_quantize_requires_imatrix((ggml_type) type) ? imatrix.data() : nullptr);
    };
    quant(f.gu_type, FF, H, blob.data());
    quant(f.gu_type, FF, H, blob.data() + f.up_off);
    quant(f.d_type, H, FF, blob.data() + f.down_off);
    return blob;
}

// The Q5_1 min term.  Activations x = d * (q + 0.45) round to q, so each q8_1 block's sum of the ORIGINAL values
// (`ds.y`, what llama.cpp CUDA multiplies the min by) exceeds d * sum(q) by 0.45 * 32 * d.  The GPU dot must take
// the quantized sum, as ggml-cpu's vec_dot does: equal to ggml-cpu on the same blocks with s = d * sum(q), and far
// from the ds.y variant.  Weights with large mins make the difference visible.
int check_q5_1_min(cudaStream_t s) {
    constexpr int n = 640, rows = 64;
    ggml_cpu_init();   // the fp16 tables vec_dot uses (the other modes get this through native_fmt)
    std::mt19937 rng(5);
    std::uniform_int_distribution<int> qd(-100, 100);
    std::normal_distribution<float> nd(0.f, 1.f);
    std::vector<float> w((size_t) rows * n), x(n);
    for (auto& v : w) v = 0.3f + 0.05f * nd(rng);        // positive weights: a large min per block
    const float d = 0.01f;
    for (auto& v : x) v = d * ((float) qd(rng) + 0.45f);
    const size_t row_bytes = ggml_row_size(GGML_TYPE_Q5_1, n);
    std::vector<uint8_t> wq((size_t) rows * row_bytes);
    ggml_quantize_chunk(GGML_TYPE_Q5_1, w.data(), wq.data(), 0, rows, n, nullptr);
    // the GPU: its own q8_1 quantizer, then iq_mmvq on Q5_1
    void *dw, *dx, *dxq;
    float* dy;
    cudaMalloc(&dw, wq.size());
    cudaMalloc(&dx, n * 4);
    cudaMalloc(&dxq, (size_t) n / 32 * 36);
    cudaMalloc((void**) &dy, rows * 4);
    cudaMemcpy(dw, wq.data(), wq.size(), cudaMemcpyHostToDevice);
    cudaMemcpy(dx, x.data(), n * 4, cudaMemcpyHostToDevice);
    strata::kernels::quantize_q8_1_rows((const float*) dx, 1, n, dxq, s);
    strata::kernels::iq_mmvq(GGML_TYPE_Q5_1, dw, dxq, dy, n, rows, 1, s);
    cudaStreamSynchronize(s);
    std::vector<float> gpu(rows);
    std::vector<uint8_t> xq((size_t) n / 32 * 36);
    cudaMemcpy(gpu.data(), dy, rows * 4, cudaMemcpyDeviceToHost);
    cudaMemcpy(xq.data(), dxq, xq.size(), cudaMemcpyDeviceToHost);
    cudaFree(dw); cudaFree(dx); cudaFree(dxq); cudaFree(dy);
    // ggml-cpu on the GPU's own blocks: once with s = d * sum(q) (the quantized sum), once with s = ds.y as stored
    struct Q81 { ggml_fp16_t d, s; int8_t qs[32]; };   // ggml's block_q8_1: {d, s} halves, 32 codes
    static_assert(sizeof(Q81) == 36, "block_q8_1 layout");
    auto* blocks = (Q81*) xq.data();
    std::vector<Q81> qsum(blocks, blocks + n / 32);
    double shift = 0.0;
    for (auto& b : qsum) {
        int sq = 0;
        for (int i = 0; i < 32; ++i) sq += b.qs[i];
        const float dd = ggml_fp16_to_fp32(b.d);
        shift = (std::max)(shift, (double) std::fabs(ggml_fp16_to_fp32(b.s) - dd * sq));
        b.s = ggml_fp32_to_fp16(dd * (float) sq);
    }
    const auto* tc = ggml_get_type_traits_cpu(GGML_TYPE_Q5_1);
    std::vector<float> want(rows), stored(rows);
    for (int r = 0; r < rows; ++r) {
        const uint8_t* row = wq.data() + (size_t) r * row_bytes;
        tc->vec_dot(n, &want[r], 0, row, 0, qsum.data(), 0, 1);
        tc->vec_dot(n, &stored[r], 0, row, 0, blocks, 0, 1);
    }
    const double e_q = rel(gpu, want), e_s = rel(gpu, stored);
    // the quantized sum goes through fp16 in ggml-cpu's block (s is a half), so 1e-3 rather than bitwise
    const bool ok = e_q < 1e-3 && e_s > 10 * e_q && shift > 0.0;
    std::printf("q5_1 min   row 0: GPU %.6g, ggml-cpu (quantized sum) %.6g, (stored sum) %.6g\n", gpu[0], want[0],
                stored[0]);
    std::printf("q5_1 min   GPU vs ggml-cpu with s = d*sum(q): rel %.2e; vs s = sum(x) (llama.cpp CUDA's): rel %.2e "
                "(largest per-block sum shift %.3g)  %s\n", e_q, e_s, shift, ok ? "ok" : "FAIL");
    return ok ? 0 : 1;
}
// #290: the BF16 token embedding (--embd-gguf) - iq_embed_rows and iq_dequant_f32 on a random BF16 table against
// the exact widening (bits << 16), every bit; rows gathered out of order, with repeats
int check_bf16_embd(cudaStream_t s) {
    constexpr int kBf16 = 30;
    const int64_t H = 2560, V = 61, NT = 97;
    int failures = 0;
    if (!strata::kernels::embed_type_supported(kBf16) || strata::kernels::iq_supported(kBf16) ||
        strata::kernels::iq_row_bytes(kBf16, H) != (size_t) H * 2) {
        std::printf("bf16 embedding: type support / row bytes wrong\n");
        return 1;
    }
    std::mt19937 rng(290);
    std::vector<uint16_t> table((size_t) (V * H));
    for (auto& v : table) {   // any bit pattern but NaN (a NaN's payload is not what the test is about)
        do v = (uint16_t) (rng() & 0xffff); while ((v & 0x7f80) == 0x7f80 && (v & 0x7f));
    }
    std::vector<int32_t> tok((size_t) NT);
    for (auto& t : tok) t = (int32_t) (rng() % V);
    void* dt = nullptr;
    int32_t* dtok = nullptr;
    float* dout = nullptr;
    cudaMalloc(&dt, table.size() * 2);
    cudaMalloc((void**) &dtok, tok.size() * 4);
    const int64_t out_rows = NT > V ? NT : V;   // the gathered rows (NT) and the whole table (V) share the buffer
    cudaMalloc((void**) &dout, (size_t) (out_rows * H) * 4);
    cudaMemcpy(dt, table.data(), table.size() * 2, cudaMemcpyHostToDevice);
    cudaMemcpy(dtok, tok.data(), tok.size() * 4, cudaMemcpyHostToDevice);
    auto widen = [](uint16_t b) { const uint32_t u = (uint32_t) b << 16; float f; std::memcpy(&f, &u, 4); return f; };
    std::vector<float> got((size_t) (out_rows * H));
    strata::kernels::iq_embed_rows(kBf16, dt, (size_t) H * 2, dtok, NT, H, dout, s);
    cudaStreamSynchronize(s);
    cudaMemcpy(got.data(), dout, (size_t) (NT * H) * 4, cudaMemcpyDeviceToHost);
    size_t rows_differ = 0;
    for (int64_t r = 0; r < NT; ++r)
        for (int64_t d = 0; d < H; ++d) {
            const float want = widen(table[(size_t) (tok[(size_t) r] * H + d)]);
            if (std::memcmp(&got[(size_t) (r * H + d)], &want, 4) != 0) { ++rows_differ; break; }
        }
    strata::kernels::iq_dequant_f32(kBf16, dt, V * H, dout, s);
    cudaStreamSynchronize(s);
    cudaMemcpy(got.data(), dout, table.size() * 4, cudaMemcpyDeviceToHost);
    size_t values_differ = 0;
    for (size_t i = 0; i < table.size(); ++i) {
        const float want = widen(table[i]);
        values_differ += std::memcmp(&got[i], &want, 4) != 0;
    }
    cudaFree(dt); cudaFree(dtok); cudaFree(dout);
    std::printf("bf16 embedding: %lld gathered rows, %zu differ; dequant of %lld values, %zu differ in any bit\n",
                (long long) NT, rows_differ, (long long) (V * H), values_differ);
    if (rows_differ || values_differ) ++failures;
    return failures;
}

}  // namespace

int main(int argc, char** argv) {
    setvbuf(stdout, nullptr, _IONBF, 0);   // keep the trail on a crash
    if (argc < 2) {
        std::fprintf(stderr, "usage: native_expert_parity <shard.gguf> [--expert E] [--activation-f32 FILE] [layer ...]\n"
                             "       [--dump-f32-dir DIR] writes dequantized weights, input and reference/operator outputs\n"
                             "       native_expert_parity --q8_1-quantizer --activation-f32 FILE\n"
                             "       native_expert_parity --q8_1-selector-contract\n"
                             "       STRATA_NATIVE_CPU_Q8_1_DOT=1|all|GU/DOWN[,...] selects expert-pair routes\n"
                             "       native_expert_parity --synthetic GU/DOWN ...   (ggml type names, e.g. q4_K/q5_1)\n"
                             "       native_expert_parity --synthetic-windows GU/DOWN  (Q8_1, widths 1..8)\n"
                             "       <shard.gguf> --expert E --activation-f32 FILE --windows-1-through-8\n"
                             "           (real supported expert weights and captured activation, Q8_1)\n"
                             "       <shard.gguf> --expert E --activation-f32 MATRIX --activation-rows N --token-width N\n"
                             "           (run distinct captured rows together, N=1..8)\n"
                             "       native_expert_parity --q5_1-min\n"
                             "       native_expert_parity --bf16-embd\n");
        return 2;
    }
    const std::string mode = argv[1];
    if (mode == "--q8_1-selector-contract") return check_q8_1_selector_contract() ? 1 : 0;
    // #152's width check tests the opt-in rule (the multi-token kernels from one token on)
    if (std::getenv("STRATA_IQ_MT_MIN") == nullptr) {
#ifdef _WIN32
        _putenv_s("STRATA_IQ_MT_MIN", "1");
#else
        setenv("STRATA_IQ_MT_MIN", "1", 1);
#endif
    }
    int failures = 0;
    cudaStream_t s;
    cudaStreamCreate(&s);
    if (mode == "--q5_1-min") {
        failures += check_q5_1_min(s);
    } else if (mode == "--bf16-embd") {
        failures += check_bf16_embd(s);
    } else if (mode == "--q8_1-quantizer") {
        std::string activation_path;
        for (int i = 2; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--activation-f32" && i + 1 < argc) activation_path = argv[++i];
            else { std::fprintf(stderr, "unexpected Q8_1 quantizer argument: %s\n", arg.c_str()); return 2; }
        }
        if (activation_path.empty()) { std::fprintf(stderr, "--activation-f32 is required\n"); return 2; }
        std::vector<float> activation((size_t) H);
        FILE* f = std::fopen(activation_path.c_str(), "rb");
        if (!f) { std::perror(activation_path.c_str()); return 2; }
        const size_t got = std::fread(activation.data(), sizeof(float), activation.size(), f);
        const int extra = std::fgetc(f);
        std::fclose(f);
        if (got != activation.size() || extra != EOF ||
            std::any_of(activation.begin(), activation.end(), [](float v) { return !std::isfinite(v); })) {
            std::fprintf(stderr, "%s: expected exactly %lld finite float32 values\n", activation_path.c_str(),
                         (long long) H);
            return 2;
        }
        failures += check_q8_1_quantizers(activation, s);
    } else if (mode == "--synthetic" || mode == "--synthetic-windows") {
        const bool all_windows = mode == "--synthetic-windows";
        const char* q8_1_env = std::getenv("STRATA_NATIVE_CPU_Q8_1_DOT");
        if (all_windows && (q8_1_env == nullptr || std::strcmp(q8_1_env, "0") == 0)) {
            std::fprintf(stderr, "--synthetic-windows requires a nonzero STRATA_NATIVE_CPU_Q8_1_DOT selector\n");
            return 2;
        }
        for (int i = 2; i < argc; ++i) {
            const std::string arg = argv[i];
            const size_t slash = arg.find('/');
            const int gu = slash == std::string::npos ? -1 : type_of(arg.substr(0, slash));
            const int dn = slash == std::string::npos ? -1 : type_of(arg.substr(slash + 1));
            cpu::NativeFmt f;
            std::string err;
            if (gu < 0 || dn < 0 || !cpu::native_fmt(gu, dn, H, FF, f, err) ||
                !strata::kernels::native_expert_supported(gu, dn, H, FF)) {
                std::printf("%s: %s\n", arg.c_str(), err.empty() ? "not a pair the GPU expert kernels take" : err.c_str());
                ++failures;
                continue;
            }
            const auto blob = synthetic_blob(f, i);
            if (all_windows) {
                if ((gu != GGML_TYPE_IQ2_S && gu != GGML_TYPE_IQ3_XXS && gu != GGML_TYPE_IQ3_S) ||
                    (dn != GGML_TYPE_Q2_0 && dn != GGML_TYPE_IQ4_NL) ||
                    f.gu_act != GGML_TYPE_Q8_1 || f.d_act != GGML_TYPE_Q8_1) {
                    std::fprintf(stderr, "--synthetic-windows supports IQ2_S/IQ3_XXS/IQ3_S with Q2_0 or IQ4_NL down weights and Q8_1 activations\n");
                    return 2;
                }
                failures += check_blob<1>(f, blob, i, "synthetic nt=1", s);
                failures += check_blob<2>(f, blob, i, "synthetic nt=2", s);
                failures += check_blob<3>(f, blob, i, "synthetic nt=3", s);
                failures += check_blob<4>(f, blob, i, "synthetic nt=4", s);
                failures += check_blob<5>(f, blob, i, "synthetic nt=5", s);
                failures += check_blob<6>(f, blob, i, "synthetic nt=6", s);
                failures += check_blob<7>(f, blob, i, "synthetic nt=7", s);
                failures += check_blob<8>(f, blob, i, "synthetic nt=8", s);
            } else {
                failures += check_blob<NT>(f, blob, i, "synthetic", s);
            }
        }
    } else {
        const strata::GgufModel model(strata::gguf_split_paths(argv[1]));
        std::vector<int> layers;
        int expert = E;
        std::string activation_path;
        std::string dump_f32_dir;
        int activation_rows = 1;
        int token_width = 0;
        bool all_windows = false;
        for (int i = 2; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--expert" && i + 1 < argc) expert = std::atoi(argv[++i]);
            else if (arg == "--activation-f32" && i + 1 < argc) activation_path = argv[++i];
            else if (arg == "--activation-rows" && i + 1 < argc) activation_rows = std::atoi(argv[++i]);
            else if (arg == "--token-width" && i + 1 < argc) token_width = std::atoi(argv[++i]);
            else if (arg == "--dump-f32-dir" && i + 1 < argc) dump_f32_dir = argv[++i];
            else if (arg == "--windows-1-through-8") all_windows = true;
            else layers.push_back(std::atoi(argv[i]));
        }
        if (all_windows && activation_path.empty()) {
            std::fprintf(stderr, "--windows-1-through-8 requires --activation-f32 FILE\n");
            return 2;
        }
        if (activation_rows < 1 || activation_rows > 8 || token_width < 0 || token_width > 8 ||
            (token_width != 0 && (token_width != activation_rows || activation_path.empty() || all_windows)) ||
            (token_width == 0 && activation_rows != 1)) {
            std::fprintf(stderr, "matrix activation requires --activation-rows N and matching --token-width N (1..8)\n");
            return 2;
        }
        if (expert < 0 || expert >= cpu::NE) {
            std::fprintf(stderr, "expert id %d is outside the model's %d experts\n", expert, cpu::NE);
            return 2;
        }
        std::vector<float> service_activation;
        if (!activation_path.empty()) {
            FILE* f = std::fopen(activation_path.c_str(), "rb");
            if (f == nullptr) { std::perror(activation_path.c_str()); return 2; }
            service_activation.resize((size_t) activation_rows * H);
            const size_t got = std::fread(service_activation.data(), sizeof(float), service_activation.size(), f);
            const int extra = std::fgetc(f);
            std::fclose(f);
            if (got != service_activation.size() || extra != EOF ||
                std::any_of(service_activation.begin(), service_activation.end(), [](float v) { return !std::isfinite(v); })) {
                std::fprintf(stderr, "%s: expected exactly %lld finite float32 values\n", activation_path.c_str(),
                             (long long) activation_rows * H);
                return 2;
            }
            std::printf("using captured service activation: %s (%d rows, %lld float32 values)\n",
                         activation_path.c_str(), activation_rows, (long long) service_activation.size());
        }
        if ((all_windows || token_width != 0) && layers.size() != 1) {
            std::fprintf(stderr, "the selected verifier-window mode requires exactly one explicit layer\n");
            return 2;
        }
        if (layers.empty()) layers = {0, 1, 2, 3, 20, 47};
        for (int l : layers) {
            const strata::TensorInfo* t[3] = {};
            const uint8_t* data[3] = {};
            const char* roles[3] = {"gate", "up", "down"};
            for (int r = 0; r < 3; ++r) {   // each role from the shard that holds it
                size_t at = 0;
                t[r] = model.find("blk." + std::to_string(l) + ".ffn_" + roles[r] + "_exps.weight", &at);
                if (t[r]) data[r] = model.shard(at).tensor_data(*t[r]);
            }
            if (!t[0] || !t[1] || !t[2]) { std::printf("layer %d: no expert tensors\n", l); ++failures; continue; }
            cpu::NativeFmt f;
            std::string err;
            if (!cpu::native_fmt((int) t[0]->type, (int) t[2]->type, H, FF, f, err, l)) {
                std::printf("layer %d: %s\n", l, err.c_str()); ++failures; continue;
            }
            std::vector<uint8_t> blob(f.bytes);
            std::memcpy(blob.data(), data[0] + (size_t) expert * f.up_off, f.up_off);
            std::memcpy(blob.data() + f.up_off, data[1] + (size_t) expert * f.up_off, f.up_off);
            std::memcpy(blob.data() + f.down_off, data[2] + (size_t) expert * (f.bytes - f.down_off),
                        f.bytes - f.down_off);
            const std::string label = "layer " + std::to_string(l) + " expert " + std::to_string(expert);
            if (token_width != 0) {
                switch (token_width) {
                    case 1: failures += check_blob<1>(f, blob, l, label + " nt=1", s, &service_activation, dump_f32_dir); break;
                    case 2: failures += check_blob<2>(f, blob, l, label + " nt=2", s, &service_activation, dump_f32_dir); break;
                    case 3: failures += check_blob<3>(f, blob, l, label + " nt=3", s, &service_activation, dump_f32_dir); break;
                    case 4: failures += check_blob<4>(f, blob, l, label + " nt=4", s, &service_activation, dump_f32_dir); break;
                    case 5: failures += check_blob<5>(f, blob, l, label + " nt=5", s, &service_activation, dump_f32_dir); break;
                    case 6: failures += check_blob<6>(f, blob, l, label + " nt=6", s, &service_activation, dump_f32_dir); break;
                    case 7: failures += check_blob<7>(f, blob, l, label + " nt=7", s, &service_activation, dump_f32_dir); break;
                    case 8: failures += check_blob<8>(f, blob, l, label + " nt=8", s, &service_activation, dump_f32_dir); break;
                }
            } else if (all_windows) {
                if ((f.gu_type != GGML_TYPE_IQ2_S && f.gu_type != GGML_TYPE_IQ3_XXS) ||
                    (f.d_type != GGML_TYPE_Q2_0 && f.d_type != GGML_TYPE_IQ4_NL) ||
                    f.gu_act != GGML_TYPE_Q8_1 || f.d_act != GGML_TYPE_Q8_1) {
                    std::fprintf(stderr, "%s: widths 1..8 require supported IQ2_S/IQ3_XXS pairs with Q2_0/IQ4_NL weights and Q8_1 activations\n",
                                 label.c_str());
                    return 2;
                }
                // The single-token result is the relevant CPU baseline for a
                // routed expert that appears once in a verifier window. Dump
                // that exact row when requested so it can be compared with a
                // service-side owner capture, rather than the later N-token
                // row written by the default check_blob<3> path.
                failures += check_blob<1>(f, blob, l, label + " nt=1", s, &service_activation, dump_f32_dir);
                failures += check_blob<2>(f, blob, l, label + " nt=2", s, &service_activation);
                failures += check_blob<3>(f, blob, l, label + " nt=3", s, &service_activation);
                failures += check_blob<4>(f, blob, l, label + " nt=4", s, &service_activation);
                failures += check_blob<5>(f, blob, l, label + " nt=5", s, &service_activation);
                failures += check_blob<6>(f, blob, l, label + " nt=6", s, &service_activation);
                failures += check_blob<7>(f, blob, l, label + " nt=7", s, &service_activation);
                failures += check_blob<8>(f, blob, l, label + " nt=8", s, &service_activation);
            } else {
                failures += check_blob<NT>(f, blob, l, label, s,
                                           service_activation.empty() ? nullptr : &service_activation, dump_f32_dir);
            }
        }
    }
    std::printf("native_expert_parity: %d failures\n", failures);
    return failures ? 1 : 0;
}

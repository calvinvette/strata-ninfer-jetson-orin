// src/kernels/cpu/native_expert.cpp - plan v0.3 P6: native (GGUF-form) experts on the CPU through ggml-cpu.
// See the header. The default activation quantizers and row dot products are ggml-cpu's. Explicitly opt-in Q8_1
// diagnostic routes for Q2_0/Q2_0 and selected IQ/Q2_0 or IQ/IQ4_NL pairs are implemented below for cross-backend
// tests.
#include "strata/kernels/cpu/native_expert.hpp"
#include "strata/kernels/cpu/expert.hpp"
#include "strata/platform/cpu_arch.hpp"
#include "strata/kernels/cpu/iq_avx512.hpp"
#include "strata/kernels/cpu/iq_avx2.hpp"
#include "strata/kernels/cpu/kq_avx2.hpp"
#include "strata/kernels/cpu/expert_layout.hpp"

#include "ggml.h"
#include "ggml-cpu.h"

#define GGML_COMMON_DECL_CPP
#define GGML_COMMON_IMPL_CPP
#include "ggml-common.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cerrno>
#include <climits>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <mutex>
#include <vector>

namespace strata::kernels::cpu {
namespace {

const ggml_type_traits_cpu* traits(int type) { return ggml_get_type_traits_cpu((ggml_type) type); }

bool q8_1_selector_known_one(const char* selector) {
    if (std::strcmp(selector, "0") == 0 || std::strcmp(selector, "1") == 0 ||
        std::strcmp(selector, "all") == 0 || std::strcmp(selector, "q2_0/q2_0") == 0 ||
        std::strcmp(selector, "iq2_s/q2_0") == 0 ||
        std::strcmp(selector, "iq2_s/iq4_nl") == 0 || std::strcmp(selector, "iq3_xxs/q2_0") == 0 ||
        std::strcmp(selector, "iq3_xxs/iq4_nl") == 0 || std::strcmp(selector, "iq3_s/q2_0") == 0 ||
        std::strcmp(selector, "iq3_s/iq4_nl") == 0)
        return true;
    const char* at = std::strstr(selector, "@layer=");
    if (at == nullptr || at == selector) return false;
    const char* n = at + 7;
    if (*n == '\0') return false;
    for (const char* p = n; *p != '\0'; ++p) if (*p < '0' || *p > '9') return false;
    errno = 0;
    char* end = nullptr;
    const long layer = std::strtol(n, &end, 10);
    if (errno == ERANGE || end == n || *end != '\0' || layer > INT_MAX) return false;
    const std::string pair(selector, (size_t) (at - selector));
    return pair == "q2_0/q2_0" || pair == "iq2_s/q2_0" || pair == "iq2_s/iq4_nl" || pair == "iq3_xxs/q2_0" ||
           pair == "iq3_xxs/iq4_nl" || pair == "iq3_s/q2_0" || pair == "iq3_s/iq4_nl";
}

bool q8_1_selector_known(const char* selector) {
    if (std::strchr(selector, ',') == nullptr) return q8_1_selector_known_one(selector);
    const std::string list(selector);
    size_t begin = 0;
    while (begin <= list.size()) {
        const size_t end = list.find(',', begin);
        const std::string item = list.substr(begin, end == std::string::npos ? end : end - begin);
        if (item.empty() || !q8_1_selector_known_one(item.c_str())) return false;
        if (end == std::string::npos) break;
        begin = end + 1;
    }
    return true;
}

bool parse_layer_selector(const char* value, int& layer) {
    if (value == nullptr) return false;
    if (*value == '\0') return false;
    for (const char* p = value; *p != '\0'; ++p) if (*p < '0' || *p > '9') return false;
    errno = 0;
    char* end = nullptr;
    const long parsed = std::strtol(value, &end, 10);
    if (errno == ERANGE || end == value || *end != '\0' || parsed > INT_MAX) return false;
    layer = (int) parsed;
    return true;
}

bool q8_1_selector_matches_one(const char* selector, int gu_type, int d_type, int layer) {
    const char* at = std::strstr(selector, "@layer=");
    if (at != nullptr) {
        char* end = nullptr;
        const long selected_layer = std::strtol(at + 7, &end, 10);
        if (end == at + 7 || *end != '\0' || selected_layer != layer) return false;
    }
    const bool q2_0_q2_0 = gu_type == GGML_TYPE_Q2_0 && d_type == GGML_TYPE_Q2_0;
    const bool iq2_s_q2_0 = gu_type == GGML_TYPE_IQ2_S && d_type == GGML_TYPE_Q2_0;
    const bool iq2_s_iq4_nl = gu_type == GGML_TYPE_IQ2_S && d_type == GGML_TYPE_IQ4_NL;
    const bool iq3_xxs_q2_0 = gu_type == GGML_TYPE_IQ3_XXS && d_type == GGML_TYPE_Q2_0;
    const bool iq3_xxs_iq4_nl = gu_type == GGML_TYPE_IQ3_XXS && d_type == GGML_TYPE_IQ4_NL;
    const bool iq3_s_q2_0 = gu_type == GGML_TYPE_IQ3_S && d_type == GGML_TYPE_Q2_0;
    const bool iq3_s_iq4_nl = gu_type == GGML_TYPE_IQ3_S && d_type == GGML_TYPE_IQ4_NL;
    const std::string pair = at == nullptr ? selector : std::string(selector, (size_t) (at - selector));
    if (pair == "1" || pair == "all")
        return q2_0_q2_0 || iq2_s_q2_0 || iq2_s_iq4_nl || iq3_xxs_q2_0 || iq3_xxs_iq4_nl || iq3_s_q2_0 || iq3_s_iq4_nl;
    if (pair == "q2_0/q2_0") return q2_0_q2_0;
    if (pair == "iq2_s/q2_0") return iq2_s_q2_0;
    if (pair == "iq2_s/iq4_nl") return iq2_s_iq4_nl;
    if (pair == "iq3_xxs/q2_0") return iq3_xxs_q2_0;
    if (pair == "iq3_xxs/iq4_nl") return iq3_xxs_iq4_nl;
    if (pair == "iq3_s/q2_0") return iq3_s_q2_0;
    if (pair == "iq3_s/iq4_nl") return iq3_s_iq4_nl;
    return false;
}

bool q8_1_selector_matches(const char* selector, int gu_type, int d_type, int layer) {
    if (std::strchr(selector, ',') == nullptr)
        return q8_1_selector_matches_one(selector, gu_type, d_type, layer);
    const std::string list(selector);
    size_t begin = 0;
    while (begin <= list.size()) {
        const size_t end = list.find(',', begin);
        const std::string item = list.substr(begin, end == std::string::npos ? end : end - begin);
        if (q8_1_selector_matches_one(item.c_str(), gu_type, d_type, layer)) return true;
        if (end == std::string::npos) break;
        begin = end + 1;
    }
    return false;
}

struct Q81Block { ggml_fp16_t d, s; int8_t qs[32]; };
static_assert(sizeof(Q81Block) == 36, "GGML Q8_1 block layout");

float q8_1_iq2_s_cuda_dot(const uint8_t* row, const uint8_t* xq, int n) {
    constexpr int qk = QK_K;
    static_assert(qk == 256, "IQ2_S CUDA contract assumes 256-value weight blocks");
    if (n % qk != 0) std::abort();
    const int nb = n / qk;
    std::array<float, 32> lane_sum{};
    for (int lane = 0; lane < 32; ++lane) {
        for (int k = lane; k < nb * 8; k += 32) {
            const int kbx = k / 8;
            const int iqs = 2 * (k % 8);
            const auto* bq2 = reinterpret_cast<const block_iq2_s*>(row) + kbx;
            const auto* act = reinterpret_cast<const Q81Block*>(xq) + kbx * 8 + iqs / 2;
            const uint8_t* qs = bq2->qs + 4 * (iqs / 2);
            const uint8_t qh = bq2->qh[iqs / 2];
            const uint8_t* packed_signs = bq2->qs + 32 + 4 * (iqs / 2);
            const int ls0 = bq2->scales[iqs / 2] & 0x0f;
            const int ls1 = bq2->scales[iqs / 2] >> 4;
            int sumi0 = 0, sumi1 = 0;
            for (int l0 = 0; l0 < 8; l0 += 2) {
                const int grid_index = qs[l0 / 2] | ((qh << (8 - l0)) & 0x300);
                const uint64_t grid = iq2s_grid[grid_index];
                const uint8_t signs = packed_signs[l0 / 2];
                const int q8_offset = l0 * 4;
                for (int j = 0; j < 4; ++j) {
                    int gl = (int) ((grid >> (8 * j)) & 0xff);
                    int gh = (int) ((grid >> (8 * (j + 4))) & 0xff);
                    if ((signs >> j) & 1) gl = -gl;
                    if ((signs >> (j + 4)) & 1) gh = -gh;
                    const int part = l0 < 4 ? 0 : 1;
                    if (part == 0) {
                        sumi0 += gl * act->qs[q8_offset + j] + gh * act->qs[q8_offset + 4 + j];
                    } else {
                        sumi1 += gl * act->qs[q8_offset + j] + gh * act->qs[q8_offset + 4 + j];
                    }
                }
            }
            const int sumi = (sumi0 * ls0 + sumi1 * ls1 + (sumi0 + sumi1) / 2) / 4;
            const float d = ggml_fp16_to_fp32(bq2->d) * ggml_fp16_to_fp32(act->d);
            lane_sum[(size_t) lane] += d * (float) sumi;
        }
    }
    for (int offset = 16; offset > 0; offset >>= 1) {
        const auto previous = lane_sum;
        for (int lane = 0; lane < 32; ++lane) lane_sum[(size_t) lane] = previous[(size_t) lane] + previous[(size_t) (lane ^ offset)];
    }
    return lane_sum[0];
}

// The opt-in CUDA-order expert mirror consumes the grouped CUDA Q8_1 producer's
// bytes. GGML's Orin NEON producer uses reciprocal-multiply plus ties-to-even;
// grouped CUDA uses roundf(x / d). Keep the activation contract aligned at this
// seam while leaving all non-Q8_1/default routes on ggml-cpu.
void quantize_q8_1_cuda_order(const float* x, int n, void* dst) {
    if (n % 32 != 0) std::abort();
    auto* blocks = static_cast<Q81Block*>(dst);
    for (int block = 0; block < n / 32; ++block) {
        const float* row = x + (size_t) block * 32;
        float amax = 0.f;
        std::array<float, 32> sums{};
        for (int lane = 0; lane < 32; ++lane) {
            amax = std::max(amax, std::fabs(row[lane]));
            sums[(size_t) lane] = row[lane];
        }
        for (int offset = 16; offset > 0; offset >>= 1) {
            const auto prior = sums;
            for (int lane = 0; lane < 32; ++lane)
                sums[(size_t) lane] = prior[(size_t) lane] + prior[(size_t) (lane ^ offset)];
        }
        const float d = amax / 127.f;
        blocks[block].d = ggml_fp32_to_fp16(std::fabs(d) > 65504.f ? std::copysign(65504.f, d) : d);
        const float sum = sums[0];
        blocks[block].s = ggml_fp32_to_fp16(std::fabs(sum) > 65504.f ? std::copysign(65504.f, sum) : sum);
        for (int lane = 0; lane < 32; ++lane) {
            const int q = amax == 0.f ? 0 : std::clamp((int) std::round(row[lane] / d), -127, 127);
            blocks[block].qs[lane] = (int8_t) q;
        }
    }
}

float q8_1_iq3_xxs_cuda_dot(const uint8_t* row, const uint8_t* xq, int n) {
    // Mirrors vec_dot_iq3_xxs_q8_1 / Fmt<18> in cuda/iq_kernels.cu for the opt-in CPU-owner diagnostic.
    constexpr int qk = QK_K;
    static_assert(qk == 256, "IQ3_XXS CUDA contract assumes 256-value weight blocks");
    if (n % qk != 0) std::abort();
    const int nb = n / qk;
    const auto* weights = reinterpret_cast<const block_iq3_xxs*>(row);
    const auto* acts = reinterpret_cast<const Q81Block*>(xq);
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
                // CUDA unpack_ksigns replaces bit 7 with parity; only its lower seven bits are sign data.
                const uint8_t sign_bits = raw_signs ^ ((uint8_t) (__builtin_popcount((unsigned) raw_signs) & 1) << 7);
                const uint32_t grid_l = iq3xxs_grid[q3[l0 + 0]];
                const uint32_t grid_h = iq3xxs_grid[q3[l0 + 1]];
                for (int j = 0; j < 4; ++j) {
                    int gl = (int8_t) (grid_l >> (8 * j));
                    int gh = (int8_t) (grid_h >> (8 * j));
                    if ((sign_bits >> j) & 1) gl = -gl;
                    if ((sign_bits >> (j + 4)) & 1) gh = -gh;
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

float q8_1_iq3_s_cuda_dot(const uint8_t* row, const uint8_t* xq, int n) {
    // Mirror vec_dot_iq3_s_q8_1 / Fmt<21> in cuda/iq_kernels.cu and the
    // grouped expert's 32-lane strided accumulation plus XOR reduction.
    constexpr int qk = QK_K;
    static_assert(qk == 256, "IQ3_S CUDA contract assumes 256-value weight blocks");
    if (n % qk != 0) std::abort();
    const int nb = n / qk;
    const auto* weights = reinterpret_cast<const block_iq3_s*>(row);
    const auto* acts = reinterpret_cast<const Q81Block*>(xq);
    std::array<float, 32> lane_sum{};
    for (int lane = 0; lane < 32; ++lane) {
        for (int k = lane; k < nb * 8; k += 32) {
            const int kbx = k / 8;
            const int iqs = 2 * (k % 8);
            const auto* w = weights + kbx;
            const auto* x = acts + kbx * 8 + iqs / 2;
            const uint8_t* qs = w->qs + 4 * iqs;
            const uint8_t qh = w->qh[iqs / 2];
            const uint8_t* signs = w->signs + 4 * (iqs / 2);
            int sumi = 0;
            for (int l0 = 0; l0 < 8; l0 += 2) {
                const uint32_t grid_l = iq3s_grid[qs[l0] | ((qh << (8 - l0)) & 0x100)];
                const uint32_t grid_h = iq3s_grid[qs[l0 + 1] | ((qh << (7 - l0)) & 0x100)];
                const uint8_t sign = signs[l0 / 2];
                for (int j = 0; j < 4; ++j) {
                    int gl = (int) ((grid_l >> (8 * j)) & 0xff);
                    int gh = (int) ((grid_h >> (8 * j)) & 0xff);
                    if ((sign >> j) & 1) gl = -gl;
                    if ((sign >> (j + 4)) & 1) gh = -gh;
                    sumi += gl * (int) x->qs[4 * l0 + j];
                    sumi += gh * (int) x->qs[4 * (l0 + 1) + j];
                }
            }
            const int scale = 1 + 2 * ((w->scales[iqs / 4] >> ((iqs << 1) & 0x04)) & 0x0f);
            sumi *= scale;
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

float q8_1_q2_0_cuda_dot(const uint8_t* row, const uint8_t* xq, int n) {
    constexpr int qk = QK2_0;
    if (n % qk != 0) std::abort();
    const int nb = n / qk;
    constexpr int8_t lut[4] = {-1, 0, 1, 2};
    std::array<float, 32> lane_sum{};
    for (int lane = 0; lane < 32; ++lane) {
        for (int k = lane; k < nb * 2; k += 32) {
            const int kbx = k / 2;
            const int iqs = k % 2;
            const auto* bq2 = reinterpret_cast<const block_q2_0*>(row) + kbx;
            const auto* act = reinterpret_cast<const Q81Block*>(xq) + kbx * 2 + iqs;
            int sumi = 0;
            for (int j = 0; j < 4; ++j) {
                const uint16_t q = (uint16_t) bq2->qs[iqs * 8 + j * 2] |
                                   ((uint16_t) bq2->qs[iqs * 8 + j * 2 + 1] << 8);
                // CUDA byte_perm(0x5140/0x7362) interleaves even and odd 2-bit
                // fields into the two four-byte activation chunks.
                for (int i = 0; i < 4; ++i) {
                    const int code0 = lut[(q >> (2 * i)) & 3];
                    const int code1 = lut[(q >> (2 * (i + 4))) & 3];
                    sumi += code0 * act->qs[j * 8 + i] + code1 * act->qs[j * 8 + 4 + i];
                }
            }
            const float d = ggml_fp16_to_fp32(bq2->d) * ggml_fp16_to_fp32(act->d);
            lane_sum[(size_t) lane] += d * (float) sumi;
        }
    }
    for (int offset = 16; offset > 0; offset >>= 1) {
        const auto previous = lane_sum;
        for (int lane = 0; lane < 32; ++lane) lane_sum[(size_t) lane] = previous[(size_t) lane] + previous[(size_t) (lane ^ offset)];
    }
    return lane_sum[0];
}

float q8_1_iq4_nl_cuda_dot(const uint8_t* row, const uint8_t* xq, int n) {
    constexpr int qk = QK4_NL;
    static_assert(qk == 32, "IQ4_NL CUDA contract assumes 32-value weight blocks");
    if (n % qk != 0) std::abort();
    const int blocks = n / qk;
    const auto* weights = reinterpret_cast<const block_iq4_nl*>(row);
    const auto* acts = reinterpret_cast<const Q81Block*>(xq);

    // Match native_down_multi_kernel's IQ4_NL row_dot_multi path, which is the
    // grouped expert kernel used by the service. Each output row uses one warp;
    // each lane walks k = lane, lane + 32, ... across the 2 sub-blocks per
    // Q8_1 block, then the warp reduces with the CUDA XOR tree. This differs
    // from standalone native_small_mmvq's four-warp mapping.
    std::array<float, 32> lane_sum{};
    for (int lane = 0; lane < 32; ++lane) {
        float acc = 0.0f;
        for (int k = lane; k < blocks * 2; k += 32) {
            const int block = k / 2;
            const int iqs = 2 * (k % 2);
            const auto* w = weights + block;
            const auto* x = acts + block;
            int sumi = 0;
            for (int i = 0; i < 2; ++i) {
                const int group = iqs + i;
                const uint8_t* packed = w->qs + 4 * group;
                for (int j = 0; j < 4; ++j) {
                    sumi += (int) kvalues_iq4nl[packed[j] & 0x0f] * (int) x->qs[4 * group + j];
                    sumi += (int) kvalues_iq4nl[packed[j] >> 4] * (int) x->qs[16 + 4 * group + j];
                }
            }
            const float d = ggml_fp16_to_fp32(w->d) * ggml_fp16_to_fp32(x->d);
            acc += d * (float) sumi;
        }
        lane_sum[(size_t) lane] = acc;
    }
    for (int offset = 16; offset > 0; offset >>= 1) {
        const auto previous = lane_sum;
        for (int lane = 0; lane < 32; ++lane) {
            lane_sum[(size_t) lane] = previous[(size_t) lane] + previous[(size_t) (lane ^ offset)];
        }
    }
    return lane_sum[0];
}

bool q8_1_scalar_dot(const NativeFmt& f) {
    const bool q2_0_pair = f.gu_type == GGML_TYPE_Q2_0 && f.d_type == GGML_TYPE_Q2_0;
    const bool iq2_s_pair = f.gu_type == GGML_TYPE_IQ2_S &&
                            (f.d_type == GGML_TYPE_Q2_0 || f.d_type == GGML_TYPE_IQ4_NL);
    const bool iq3_xxs_pair = f.gu_type == GGML_TYPE_IQ3_XXS &&
                              (f.d_type == GGML_TYPE_Q2_0 || f.d_type == GGML_TYPE_IQ4_NL);
    const bool iq3_s_pair = f.gu_type == GGML_TYPE_IQ3_S &&
                            (f.d_type == GGML_TYPE_Q2_0 || f.d_type == GGML_TYPE_IQ4_NL);
    return (q2_0_pair || iq2_s_pair || iq3_xxs_pair || iq3_s_pair) &&
           f.gu_act == GGML_TYPE_Q8_1 && f.d_act == GGML_TYPE_Q8_1;
}

void init_once() {
    static std::once_flag once;
    std::call_once(once, [] { ggml_cpu_init(); });
}

}  // namespace

bool native_experts_available() noexcept { return true; }

// The "is this format handled by that kernel" questions, answered here and not next to the kernels: iq_avx512.cpp is
// compiled for AVX-512 and iq_avx2.cpp / kq_avx2.cpp for AVX2, and native_gu_rows asks these on every CPU before it
// has checked what the CPU can run.  A function in a wide-ISA file may use that ISA anywhere in its body, so an
// answer that is only a comparison must not come from one (#795).
bool iq512_supported(int type) noexcept {
    return type == 16 || type == 17 || type == 18 || type == 21 || type == 22;
}

bool iq256_supported(int type) noexcept {
    return type == 16 || type == 17 || type == 18 || type == 21 || type == 22 || type == 23;
}

bool kq256_supported(int type) noexcept { return type == 12 || type == 7 || type == 8; }

bool native_fmt(int gu_type, int d_type, int64_t n_embd, int64_t n_ff, NativeFmt& f, std::string& err, int layer) {
    init_once();
    const ggml_type_traits_cpu* tg = traits(gu_type);
    const ggml_type_traits_cpu* td = traits(d_type);
    if (tg == nullptr || tg->vec_dot == nullptr || td == nullptr || td->vec_dot == nullptr) {
        err = "native experts: ggml-cpu has no dot product for type " + std::to_string(tg && tg->vec_dot ? d_type : gu_type);
        return false;
    }
    const ggml_type_traits_cpu* ag = traits(tg->vec_dot_type);
    const ggml_type_traits_cpu* ad = traits(td->vec_dot_type);
    if (ag == nullptr || ag->from_float == nullptr || ad == nullptr || ad->from_float == nullptr) {
        err = "native experts: ggml-cpu cannot quantize an activation for this layer";
        return false;
    }
    if (n_embd % ggml_blck_size((ggml_type) gu_type) || n_ff % ggml_blck_size((ggml_type) d_type) ||
        n_embd % ggml_blck_size(tg->vec_dot_type) || n_ff % ggml_blck_size(td->vec_dot_type)) {
        err = "native experts: expert geometry is not whole blocks";
        return false;
    }
    f.gu_type = gu_type;
    f.d_type = d_type;
    f.gu_act = (int) tg->vec_dot_type;
    f.d_act = (int) td->vec_dot_type;
    const char* q8_1_probe = std::getenv("STRATA_NATIVE_CPU_Q8_1_DOT");
    if (q8_1_probe != nullptr && !q8_1_selector_known(q8_1_probe)) {
        err = "native experts: STRATA_NATIVE_CPU_Q8_1_DOT must be 0, 1, all, a supported GU/DOWN pair "
              "(optionally followed by @layer=N), or a comma-separated list of those selectors";
        return false;
    }
    if (q8_1_probe != nullptr && std::strcmp(q8_1_probe, "0") != 0 &&
        q8_1_selector_matches(q8_1_probe, gu_type, d_type, layer)) {
        f.gu_act = GGML_TYPE_Q8_1;
        f.d_act = GGML_TYPE_Q8_1;
    }
    const char* reciprocal_silu_layer = std::getenv("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER");
    const char* reciprocal_silu_expert = std::getenv("STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_EXPERT");
    if (reciprocal_silu_layer != nullptr) {
        int selected_layer = -1;
        if (!parse_layer_selector(reciprocal_silu_layer, selected_layer)) {
            err = "native experts: STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER must be a non-negative layer number";
            return false;
        }
        f.q8_1_reciprocal_silu = selected_layer == layer && f.gu_act == GGML_TYPE_Q8_1 &&
                                 f.d_act == GGML_TYPE_Q8_1;
    }
    if (reciprocal_silu_expert != nullptr &&
        !parse_layer_selector(reciprocal_silu_expert, f.q8_1_reciprocal_silu_expert)) {
        err = "native experts: STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_EXPERT must be a non-negative expert number";
        return false;
    }
    const char* exp2f_silu_layer = std::getenv("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER");
    const char* exp2f_silu_expert = std::getenv("STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT");
    if (exp2f_silu_layer != nullptr) {
        int selected_layer = -1;
        if (!parse_layer_selector(exp2f_silu_layer, selected_layer)) {
            err = "native experts: STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER must be a non-negative layer number";
            return false;
        }
        f.q8_1_exp2f_silu = selected_layer == layer && f.gu_act == GGML_TYPE_Q8_1 &&
                            f.d_act == GGML_TYPE_Q8_1;
    }
    if (exp2f_silu_expert != nullptr &&
        !parse_layer_selector(exp2f_silu_expert, f.q8_1_exp2f_silu_expert)) {
        err = "native experts: STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT must be a non-negative expert number";
        return false;
    }
    if (f.q8_1_exp2f_silu && f.q8_1_reciprocal_silu) {
        err = "native experts: exp2f and reciprocal SiLU probes cannot both select the same layer";
        return false;
    }
    f.n_embd = n_embd;
    f.n_ff = n_ff;
    f.gu_row = ggml_row_size((ggml_type) gu_type, n_embd);
    f.d_row = ggml_row_size((ggml_type) d_type, n_ff);
    f.up_off = f.gu_row * (size_t) n_ff;
    f.down_off = 2 * f.up_off;
    f.bytes = f.down_off + f.d_row * (size_t) n_embd;
    f.act_bytes = ggml_row_size((ggml_type) f.gu_act, n_embd);
    f.h_bytes = ggml_row_size((ggml_type) f.d_act, n_ff);
    if (f.act_bytes > kNativeActBytes || f.h_bytes > kNativeHBytes) {
        err = "native experts: activation larger than the pool's buffers";
        return false;
    }
    return true;
}

namespace {
// Q8_K (the activations of every i-quant row): ggml-cpu's x86 quantizer is the scalar reference, ~3 us per token
// and layer on the host before the pool can start; q8k_quant_avx2 writes the same bytes.  cpu_avx2_ok() too:
// iq_avx2.cpp is compiled for AVX2 (an AVX-only CPU, or STRATA_FORCE_ISA=avx, keeps ggml's).  STRATA_NO_Q8K_AVX2=1:
// ggml's on any CPU.
bool q8k_avx2(int type) {
    static const bool on = cpu_avx2_ok() && std::getenv("STRATA_NO_Q8K_AVX2") == nullptr;
    return on && type == (int) GGML_TYPE_Q8_K;
}
}  // namespace

void native_quant_act(const NativeFmt& f, const float* x, void* dst) {
    if (f.gu_act == GGML_TYPE_Q8_1) { quantize_q8_1_cuda_order(x, (int) f.n_embd, dst); return; }
#if STRATA_CPU_X86
    if (q8k_avx2(f.gu_act)) { q8k_quant_avx2(x, dst, f.n_embd); return; }
#endif
    traits(f.gu_act)->from_float(x, dst, f.n_embd);
}

void native_quant_h(const NativeFmt& f, const float* h, void* dst) {
    if (f.d_act == GGML_TYPE_Q8_1) { quantize_q8_1_cuda_order(h, (int) f.n_ff, dst); return; }
#if STRATA_CPU_X86
    if (q8k_avx2(f.d_act)) { q8k_quant_avx2(h, dst, f.n_ff); return; }
#endif
    traits(f.d_act)->from_float(h, dst, f.n_ff);
}

int native_gu_mt_min(int gu_type) {
    // #152: from how many tokens the multi-token kernels run (ggml's vec_dot below that).  The default 2 is the
    // measured-fastest rule, but a token's expert rows then round differently alone than in a group, so greedy output
    // can depend on how many drafts a verify window held.  STRATA_IQ_MT_MIN=1 (opt-in, 0.1.30) uses the multi-token
    // kernels for every group: output independent of the drafting, at a measured -1..-3% decode on IQ3_S (AVX-512).
    static const char* env = std::getenv("STRATA_IQ_MT_MIN");
    static const int mt_min = env ? std::atoi(env) : 2;
    // IQ3_S where the AVX-2 kernel gathers its grid (cpu_gather_fast, unless STRATA_IQ256_GATHER=0) on a CPU without
    // AVX-512: there that kernel beats ggml's dot for ONE token too (14900KF P-core, an expert's gate/up rows: 0.34 ->
    // 0.19 ms; its E-cores, which keep the scalar decode: 0.71 -> 0.68), and in decode most CPU experts serve one token
    // of the window.  So IQ3_S takes it for every group, and those rows no longer depend on the drafting.  A machine-
    // wide rule, not a per-core one: every core rounds an expert the same.  Every probe here is in expert_layout.cpp
    // and cpu_avx2_ok() comes first, so no AVX2 code runs before the check.  STRATA_IQ_MT_MIN set keeps its rule.
    // Opt-in (STRATA_IQ3S_MT1=1): it changes a lone token's IQ3_S rounding on those CPUs, so the default stays 0.1.39's.
    static const bool iq3s_one = env == nullptr && std::getenv("STRATA_IQ3S_MT1") != nullptr && cpu_avx2_ok() && std::getenv("STRATA_NO_IQ256") == nullptr &&
                                 !cpu_avx512_ok() && iq256_gather_setting() != 0 && cpu_gather_fast();
    return iq3s_one && gu_type == 21 ? 1 : mt_min;
}

void native_gu_rows(const NativeFmt& f, const uint8_t* blob, const void* const* act, int nt, float* const* ff,
                    int r0, int r1) {
    if (q8_1_scalar_dot(f)) {
        for (int r = r0; r < r1; ++r) {
            const uint8_t* gr = blob + (size_t) r * f.gu_row;
            const uint8_t* ur = blob + f.up_off + (size_t) r * f.gu_row;
            for (int t = 0; t < nt; ++t) {
                const auto* xq = (const uint8_t*) act[t];
                const auto dot = f.gu_type == GGML_TYPE_Q2_0 ? q8_1_q2_0_cuda_dot :
                                 f.gu_type == GGML_TYPE_IQ2_S ? q8_1_iq2_s_cuda_dot :
                                 f.gu_type == GGML_TYPE_IQ3_XXS ? q8_1_iq3_xxs_cuda_dot : q8_1_iq3_s_cuda_dot;
                const float g = dot(gr, xq, (int) f.n_embd);
                const float u = dot(ur, xq, (int) f.n_embd);
                if (f.q8_1_exp2f_silu) {
                    constexpr float kLog2E = 1.4426950408889634f;
                    const float e = std::exp2((-g) * kLog2E);
                    ff[t][r] = (g / (1.f + e)) * u;
                } else if (f.q8_1_reciprocal_silu) {
                    const float sigmoid = 1.f / (1.f + std::exp(-g));
                    ff[t][r] = (g * sigmoid) * u;
                } else {
                    ff[t][r] = (g / (1.f + std::exp(-g))) * u;
                }
            }
        }
        return;
    }
    // the multi-token kernels decode the weights once for all tokens: 2.0-2.4x ggml-cpu at three tokens, no faster
    // at one (all are bound by the codebook lookups, ~5 GB/s per core), measured by native_expert_parity.  AVX-512
    // first, then the AVX-2 one (Zen 2/3, Intel 12th-14th gen).  STRATA_NO_IQ512 drops an AVX-512 CPU to the
    // AVX-2 kernel, STRATA_NO_IQ256 drops the AVX-2 kernel; ggml-cpu's single-token vec_dot is reached only with
    // both set (and on a CPU without AVX-512, STRATA_NO_IQ512 changes nothing).
#if STRATA_CPU_X86
    static const bool avx512 = cpu_avx512_ok() && std::getenv("STRATA_NO_IQ512") == nullptr;
    // STRATA_NO_IQ256 drops the AVX-2 kernel.  cpu_avx2_ok() is ALSO required: iq_avx2.cpp and kq_avx2.cpp
    // are compiled /arch:AVX2 and use AVX2 and FMA3, so calling them on a CPU without either is an
    // illegal instruction, not a slow path.  The gate sat next to `avx512` above, which does test
    // cpu_avx512_ok(), and that asymmetry is what let a pre-Haswell CPU reach iq256_gu_rows.
    // Without it this falls through to ggml-cpu's vec_dot below, which is compiled for whatever
    // baseline the build selected (AVX1 here) and covers the same types - IQ2_XXS and IQ2_S among
    // them.  That path loops over tokens itself, so it is correct for any `nt`, not just one.
    static const bool avx2 = cpu_avx2_ok() && std::getenv("STRATA_NO_IQ256") == nullptr;
    const int mt_min = native_gu_mt_min(f.gu_type);   // #152
    // Unsloth UD-Q4_K_XL's Q4_K gate/up: the multi-token kernel is bit-exact against ggml's per-token dot (any group
    // size, no #152 rule).  Opt-in, STRATA_KQ256=1: measured no faster in the engine (a window's expert groups hold
    // ~1.4 tokens and the weights stay in L1 across ggml's per-token calls; 1.01-1.13x in native_expert_parity).
    static const bool kq = [] { const char* v = std::getenv("STRATA_KQ256"); return cpu_avx2_ok() && v != nullptr && std::atoi(v) != 0; }();
    if (kq && f.gu_type == 12 && nt >= 2) {   // one token: ggml's own dot below (the same bits, less overhead)
        kq256_gu_rows(f.gu_type, blob, f.gu_row, f.up_off, (int) f.n_embd, act, nt, ff, r0, r1);
        return;
    }
    // A format with only an AVX-2 kernel (IQ4_XS, #415) takes it on AVX-2 CPUs only: an AVX-512 CPU keeps ggml-cpu for
    // it, as before (its rows would round differently).  Each kernel only for the formats it implements: falling
    // through an empty switch would leave ff unwritten instead of falling back to ggml-cpu.
    static const bool cpu512 = cpu_avx512_ok();
    if (nt >= mt_min && (iq512_supported(f.gu_type) || (!cpu512 && iq256_supported(f.gu_type)))) {
        if (avx512 && iq512_supported(f.gu_type)) {
            iq512_gu_rows(f.gu_type, blob, f.gu_row, f.up_off, (int) f.n_embd, act, nt, ff, r0, r1);
            return;
        }
        if (avx2 && iq256_supported(f.gu_type)) {
            iq256_gu_rows(f.gu_type, blob, f.gu_row, f.up_off, (int) f.n_embd, act, nt, ff, r0, r1);
            return;
        }
    }
#endif
    const ggml_vec_dot_t dot = traits(f.gu_type)->vec_dot;
    const int n = (int) f.n_embd;
    for (int r = r0; r < r1; ++r) {
        const uint8_t* gr = blob + (size_t) r * f.gu_row;
        const uint8_t* ur = blob + f.up_off + (size_t) r * f.gu_row;
        for (int t = 0; t < nt; ++t) {
            float g = 0.f, u = 0.f;
            dot(n, &g, 0, gr, 0, act[t], 0, 1);
            dot(n, &u, 0, ur, 0, act[t], 0, 1);
            ff[t][r] = (g / (1.f + std::exp(-g))) * u;
        }
    }
}

void native_down_rows(const NativeFmt& f, const uint8_t* blob, const void* const* hq, int nt, float* const* out,
                      int r0, int r1) {
    if (q8_1_scalar_dot(f)) {
        for (int r = r0; r < r1; ++r) {
            const uint8_t* dr = blob + f.down_off + (size_t) r * f.d_row;
            for (int t = 0; t < nt; ++t) {
                out[t][r] = f.d_type == GGML_TYPE_Q2_0
                    ? q8_1_q2_0_cuda_dot(dr, (const uint8_t*) hq[t], (int) f.n_ff)
                    : q8_1_iq4_nl_cuda_dot(dr, (const uint8_t*) hq[t], (int) f.n_ff);
            }
        }
        return;
    }
    // IQ4_NL down rows: the AVX-2 multi-token kernel decodes the nibbles and absolutises the weights once per
    // block instead of once per token; ggml-cpu's dot is single-token.  STRATA_NO_IQ4NL falls back to it.
#if STRATA_CPU_X86
    static const bool iq4nl_mt = std::getenv("STRATA_NO_IQ4NL") == nullptr;
    static const int mt_min = [] { const char* e = std::getenv("STRATA_IQ_MT_MIN"); return e ? std::atoi(e) : 2; }();
    static const bool kq = [] { const char* v = std::getenv("STRATA_KQ256"); return v != nullptr && std::atoi(v) != 0; }();
    // Both multi-token kernels below are /arch:AVX2 translation units (kq_avx2.cpp and iq_avx2.cpp),
    // so a CPU without AVX2 has to reach ggml-cpu's vec_dot instead - same reasoning as the gate/up
    // rows above, where `avx512` tested cpu_avx512_ok() and `avx2` did not.
    if (cpu_avx2_ok() && kq && nt >= 2 && (f.d_type == 7 || f.d_type == 8)) {   // Q5_1 / Q8_0 down: bit-exact, any group size
        kq256_rows(f.d_type, blob + f.down_off, f.d_row, (int) f.n_ff, hq, nt, out, r0, r1);
        return;
    }
    if (cpu_avx2_ok() && nt >= mt_min && f.d_type == 20 && iq4nl_mt) {   // #152: the same rule as the gate/up rows
        iq4nl256_down_rows(blob + f.down_off, f.d_row, (int) f.n_ff, hq, nt, out, r0, r1);
        return;
    }
#endif
    const ggml_vec_dot_t dot = traits(f.d_type)->vec_dot;
    const int n = (int) f.n_ff;
    for (int r = r0; r < r1; ++r) {
        const uint8_t* dr = blob + f.down_off + (size_t) r * f.d_row;
        for (int t = 0; t < nt; ++t) {
            float s = 0.f;
            dot(n, &s, 0, dr, 0, hq[t], 0, 1);
            out[t][r] = s;
        }
    }
}

}  // namespace strata::kernels::cpu

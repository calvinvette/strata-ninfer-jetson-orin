#include "strata/kernels/cpu/expert.hpp"

#include <arm_neon.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>

namespace cpu = strata::kernels::cpu;
using Clock = std::chrono::steady_clock;

// Test-only AArch64 implementation of Strata's Q8_1 contract. In particular,
// add +/-0.5 then truncate: NEON vcvtn (nearest-even) is not equivalent.
static void quantize_neon_strata_q8_1(const float* x, int n, cpu::ActQ& out) {
    out.nchunks = n / cpu::QKA;
    alignas(16) int32_t qtmp[32];
    for (int b = 0; b < out.nchunks; ++b) {
        const float* p = x + b * 32;
        float32x4_t v[8];
        float32x4_t a[8];
        for (int j = 0; j < 8; ++j) {
            v[j] = vld1q_f32(p + 4 * j);
            a[j] = vabsq_f32(v[j]);
        }
        float32x4_t m0 = vmaxq_f32(vmaxq_f32(a[0], a[1]), vmaxq_f32(a[2], a[3]));
        float32x4_t m1 = vmaxq_f32(vmaxq_f32(a[4], a[5]), vmaxq_f32(a[6], a[7]));
        const float amax = vmaxvq_f32(vmaxq_f32(m0, m1));
        const float scale = amax > 0.f ? amax / 127.f : 0.f;
        const float inv = scale > 0.f ? 1.f / scale : 0.f;
        const float32x4_t vinv = vdupq_n_f32(inv);
        const float32x4_t zero = vdupq_n_f32(0.f);
        const float32x4_t half = vdupq_n_f32(0.5f);
        const float32x4_t mhalf = vdupq_n_f32(-0.5f);
        int32_t sum = 0;
        for (int j = 0; j < 8; ++j) {
            const float32x4_t t = vmulq_f32(v[j], vinv);
            const float32x4_t bias = vbslq_f32(vcltq_f32(t, zero), mhalf, half);
            int32x4_t qi = vcvtq_s32_f32(vaddq_f32(t, bias));
            qi = vmaxq_s32(vdupq_n_s32(-127), vminq_s32(vdupq_n_s32(127), qi));
            vst1q_s32(qtmp + 4 * j, qi);
            sum += vaddvq_s32(qi);
        }
        for (int j = 0; j < 32; ++j) out.q[b * 32 + j] = static_cast<int8_t>(qtmp[j]);
        out.scale[b] = scale;
        out.sum[b] = sum;
        out.hx[b] = scale * static_cast<float>(sum);
    }
    out.bp_pairs = 0;
}

static double run(const std::vector<float>& input, int rows, int n, int iterations, bool neon) {
    cpu::ActQ out{};
    volatile int64_t sink = 0;
    const auto start = Clock::now();
    for (int it = 0; it < iterations; ++it) {
        for (int r = 0; r < rows; ++r) {
            const float* row = input.data() + size_t(r) * n;
            if (neon) quantize_neon_strata_q8_1(row, n, out);
            else cpu::act_quant_q8_1(row, n, out);
            sink = sink + out.q[(it + r) % n] + out.sum[(r * 80) % out.nchunks];
        }
    }
    (void)sink;
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count() / iterations;
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const unsigned seed = unsigned(std::stoul(argv[1]));
    constexpr int rows = 256, n = cpu::H, iterations = 16, samples = 9;
    std::mt19937 rng(seed);
    std::vector<float> input(size_t(rows) * n);
    for (int r = 0; r < rows; ++r) {
        for (int i = 0; i < n; ++i) {
            if (r == 0) input[size_t(r) * n + i] = 0.f;
            else if (r == 1) {
                static constexpr float ties[] = {-127.f, -63.5f, -1.5f, -0.5f, 0.f, 0.5f, 1.5f, 63.5f};
                input[size_t(r) * n + i] = ties[i % 8];
            } else input[size_t(r) * n + i] = float(int(rng() % 20001) - 10000) * (1.f / 317.f);
        }
    }
    cpu::ActQ scalar{}, neon{};
    int mismatch_blocks = 0;
    for (int r = 0; r < rows; ++r) {
        const float* row = input.data() + size_t(r) * n;
        cpu::act_quant_q8_1(row, n, scalar);
        quantize_neon_strata_q8_1(row, n, neon);
        for (int b = 0; b < scalar.nchunks; ++b) {
            if (scalar.scale[b] != neon.scale[b] || scalar.sum[b] != neon.sum[b] ||
                scalar.hx[b] != neon.hx[b] ||
                std::memcmp(scalar.q + b * 32, neon.q + b * 32, 32) != 0) ++mismatch_blocks;
        }
    }
    if (mismatch_blocks) {
        std::printf("contract=Strata_Q8_1 parity=FAIL mismatched_blocks=%d\n", mismatch_blocks);
        return 1;
    }
    for (int k = 0; k < 4; ++k) { run(input, rows, n, 1, false); run(input, rows, n, 1, true); }
    std::mt19937 order_rng(seed ^ 0x3d91u);
    std::vector<double> scalar_ms, neon_ms;
    for (int s = 0; s < samples; ++s) {
        const bool scalar_first = (order_rng() & 1u) != 0;
        double a, b;
        if (scalar_first) { a = run(input, rows, n, iterations, false); b = run(input, rows, n, iterations, true); }
        else { b = run(input, rows, n, iterations, true); a = run(input, rows, n, iterations, false); }
        scalar_ms.push_back(a); neon_ms.push_back(b);
        std::printf("sample=%d order=%s scalar_ms=%.6f neon_ms=%.6f delta_pct=%.3f\n",
                    s, scalar_first ? "scalar-first" : "neon-first", a, b, (b / a - 1.0) * 100.0);
    }
    auto median = [](std::vector<double> v) { std::sort(v.begin(), v.end()); return v[v.size() / 2]; };
    std::printf("contract=Strata_Q8_1 rows=%d width=%d iterations=%d samples=%d mismatched_blocks=%d "
                "scalar_median_ms=%.6f neon_median_ms=%.6f delta_pct=%.3f\n",
                rows, n, iterations, samples, mismatch_blocks, median(scalar_ms), median(neon_ms),
                (median(neon_ms) / median(scalar_ms) - 1.0) * 100.0);
    return 0;
}

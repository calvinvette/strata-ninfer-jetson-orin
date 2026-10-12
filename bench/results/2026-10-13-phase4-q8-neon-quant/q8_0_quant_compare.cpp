#include "strata/kernels/cpu/expert.hpp"
#include "ggml.h"
#include "ggml-cpu.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <numeric>
#include <random>
#include <string>
#include <vector>

namespace cpu = strata::kernels::cpu;
using Clock = std::chrono::steady_clock;

static double run_scalar(const std::vector<float>& input, int rows, int n, int iterations) {
    cpu::ActQ actual{};
    volatile int64_t sink = 0;
    const auto start = Clock::now();
    for (int it = 0; it < iterations; ++it) {
        for (int r = 0; r < rows; ++r) {
            cpu::act_quant_q8_1(input.data() + size_t(r) * n, n, actual);
            sink = sink + actual.q[(it + r) % n] + actual.sum[(r * 80) % actual.nchunks];
        }
    }
    const auto stop = Clock::now();
    (void)sink;
    return std::chrono::duration<double, std::milli>(stop - start).count() / iterations;
}

static double run_ggml(const std::vector<float>& input, int rows, int n, int iterations,
                       const ggml_type_traits_cpu* traits, std::vector<uint8_t>& out) {
    volatile uint8_t sink = 0;
    const auto start = Clock::now();
    for (int it = 0; it < iterations; ++it) {
        for (int r = 0; r < rows; ++r) {
            traits->from_float(input.data() + size_t(r) * n, out.data(), n);
            sink = sink ^ out[(it + r) % out.size()];
        }
    }
    const auto stop = Clock::now();
    (void)sink;
    return std::chrono::duration<double, std::milli>(stop - start).count() / iterations;
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const unsigned seed = unsigned(std::stoul(argv[1]));
    constexpr int rows = 256, n = 2560, chunks = n / 32, iterations = 16, samples = 9;
    ggml_cpu_init();
    cpu::expert_set_oracle_q8_0(true);
    const auto* traits = ggml_get_type_traits_cpu(GGML_TYPE_Q8_0);
    if (!traits || !traits->from_float) return 3;

    std::mt19937 rng(seed);
    std::vector<float> input(size_t(rows) * n);
    for (int r = 0; r < rows; ++r) {
        for (int i = 0; i < n; ++i) {
            if (r == 0) input[size_t(r) * n + i] = 0.f;
            else if (r == 1) input[size_t(r) * n + i] = float((i % 32) - 16) * 0.5f;
            else input[size_t(r) * n + i] = float(int(rng() % 20001) - 10000) * (1.f / 317.f);
        }
    }
    cpu::ActQ actual{};
    std::vector<uint8_t> encoded(size_t(chunks) * 34);
    int mismatches = 0;
    for (int r = 0; r < rows; ++r) {
        const float* x = input.data() + size_t(r) * n;
        traits->from_float(x, encoded.data(), n);
        cpu::act_quant_q8_1(x, n, actual);
        for (int b = 0; b < chunks; ++b) {
            uint16_t scale_bits;
            std::memcpy(&scale_bits, encoded.data() + size_t(b) * 34, 2);
            const float scale = ggml_fp16_to_fp32(scale_bits);
            const auto* q = reinterpret_cast<const int8_t*>(encoded.data() + size_t(b) * 34 + 2);
            const int32_t sum = std::accumulate(q, q + 32, 0);
            if (std::memcmp(q, actual.q + b * 32, 32) || actual.scale[b] != scale ||
                actual.sum[b] != sum || actual.hx[b] != scale * float(sum)) ++mismatches;
        }
    }
    if (mismatches) {
        std::printf("oracle mismatches=%d\n", mismatches);
        return 1;
    }

    // Warm both implementations before randomized paired timing blocks.
    for (int k = 0; k < 4; ++k) {
        run_scalar(input, rows, n, 1);
        run_ggml(input, rows, n, 1, traits, encoded);
    }
    std::mt19937 order_rng(seed ^ 0x5a17u);
    std::vector<double> scalar_ms, ggml_ms;
    for (int sample = 0; sample < samples; ++sample) {
        const bool scalar_first = (order_rng() & 1u) != 0;
        double s, g;
        if (scalar_first) {
            s = run_scalar(input, rows, n, iterations);
            g = run_ggml(input, rows, n, iterations, traits, encoded);
        } else {
            g = run_ggml(input, rows, n, iterations, traits, encoded);
            s = run_scalar(input, rows, n, iterations);
        }
        scalar_ms.push_back(s);
        ggml_ms.push_back(g);
        std::printf("sample=%d order=%s scalar_ms=%.6f ggml_arm_ms=%.6f delta_pct=%.3f\n",
                    sample, scalar_first ? "scalar-first" : "ggml-first", s, g, (g / s - 1.0) * 100.0);
    }
    auto median = [](std::vector<double> v) {
        std::sort(v.begin(), v.end());
        return v[v.size() / 2];
    };
    std::printf("contract=bit-identical Q8_0 rows=%d width=%d iterations=%d samples=%d mismatches=%d "
                "scalar_median_ms=%.6f ggml_arm_median_ms=%.6f arm_vs_scalar_pct=%.3f\n",
                rows, n, iterations, samples, mismatches, median(scalar_ms), median(ggml_ms),
                (median(ggml_ms) / median(scalar_ms) - 1.0) * 100.0);
    cpu::expert_set_oracle_q8_0(false);
    return 0;
}

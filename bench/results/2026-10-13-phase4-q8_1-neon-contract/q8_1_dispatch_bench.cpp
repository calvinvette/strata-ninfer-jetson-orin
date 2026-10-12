#include "strata/kernels/cpu/expert.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

namespace cpu = strata::kernels::cpu;
using Clock = std::chrono::steady_clock;

static double run(const std::vector<float>& input, int rows, int iterations) {
    cpu::ActQ out{};
    volatile int64_t sink = 0;
    const auto start = Clock::now();
    for (int it = 0; it < iterations; ++it) {
        for (int r = 0; r < rows; ++r) {
            cpu::act_quant_q8_1(input.data() + size_t(r) * cpu::H, cpu::H, out);
            sink = sink + out.q[(it + r) % cpu::H] + out.sum[(r * 80) % out.nchunks];
        }
    }
    (void)sink;
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count() / iterations;
}

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    const bool neon = std::string(argv[1]) == "neon";
    const unsigned seed = unsigned(std::stoul(argv[2]));
    if (neon) setenv("STRATA_Q8_1_NEON", "1", 1);
    else unsetenv("STRATA_Q8_1_NEON");
    constexpr int rows = 256, iterations = 16, samples = 9;
    std::mt19937 rng(seed);
    std::vector<float> input(size_t(rows) * cpu::H);
    for (int r = 0; r < rows; ++r) {
        for (int i = 0; i < cpu::H; ++i) {
            if (r == 0) input[size_t(r) * cpu::H + i] = 0.f;
            else if (r == 1) {
                static constexpr float ties[] = {-127.f, -63.5f, -1.5f, -0.5f, 0.f, 0.5f, 1.5f, 63.5f};
                input[size_t(r) * cpu::H + i] = ties[i % 8];
            } else input[size_t(r) * cpu::H + i] = float(int(rng() % 20001) - 10000) * (1.f / 317.f);
        }
    }
    for (int i = 0; i < 3; ++i) (void)run(input, rows, 1);
    std::vector<double> times;
    for (int s = 0; s < samples; ++s) {
        const double ms = run(input, rows, iterations);
        times.push_back(ms);
        std::printf("mode=%s sample=%d ms_per_16x256=%.6f\n", neon ? "neon" : "scalar", s, ms);
    }
    std::sort(times.begin(), times.end());
    std::printf("mode=%s seed=%u median_ms_per_16x256=%.6f\n", neon ? "neon" : "scalar", seed,
                times[times.size() / 2]);
    return 0;
}

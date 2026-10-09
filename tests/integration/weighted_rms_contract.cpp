// Independent FP64 oracle for Strata's represented F32 weighted RMS contract.
// Contract preparation consulted NInfer b07248f2 include/ninfer/ops/rmsnorm.h;
// no NInfer kernel/test code is incorporated. See docs/integration/OPERATOR_CONTRACTS.md.
#include "strata/kernels/native_gr_norm.hpp"
#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {
constexpr double relative_l2_limit = 1e-5;
constexpr double absolute_floor = 1e-6;
constexpr double relative_max_limit = 1e-5;
constexpr int guard_words = 8;

void checked(cudaError_t code) {
    if (code != cudaSuccess) throw std::runtime_error(cudaGetErrorString(code));
}

struct Buffer {
    float* data = nullptr;
    explicit Buffer(std::size_t count) { checked(cudaMalloc(&data, count * sizeof(float))); }
    ~Buffer() { if (data) cudaFree(data); }
    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;
};

float represented_sample(std::uint32_t& seed) {
    seed ^= seed << 13;
    seed ^= seed >> 17;
    seed ^= seed << 5;
    // Dyadic values are exact F32; generation is unrelated to CUDA's reduction.
    return static_cast<float>(static_cast<int>(seed & 65535u) - 32768) / 8192.0f;
}

void evaluate(int columns, int groups, int tokens, int mode, cudaStream_t stream) {
    const std::size_t rows = std::size_t(groups) * tokens;
    const std::size_t count = rows * columns;
    std::vector<float> input(count), gamma(std::size_t(groups) * columns);
    std::uint32_t seed = 0x658fd1u + columns + 31 * groups + 17 * tokens + mode;
    for (auto& x : input) {
        x = represented_sample(seed);
        if (mode == 1) x *= 1e-10f;
        if (mode == 2) x = 0;
    }
    for (std::size_t i = 0; i < gamma.size(); ++i)
        gamma[i] = represented_sample(seed) + static_cast<float>(i / columns) / 4.0f;
    const float epsilon = 1e-6f;

    // Mathematical oracle: represented inputs promoted before all arithmetic.
    // No warp tree, F32 intermediate rounding, rsqrtf or implementation staging.
    std::vector<double> ideal(count);
    double norm_squared = 0, max_reference = 0;
    for (std::size_t row = 0; row < rows; ++row) {
        const auto offset = row * columns;
        double squares = 0;
        for (int column = 0; column < columns; ++column) {
            const double x = input[offset + column];
            squares += x * x;
        }
        const double denominator = std::sqrt(squares / columns + static_cast<double>(epsilon));
        const auto gain_offset = (row % groups) * columns;
        for (int column = 0; column < columns; ++column) {
            const double y = static_cast<double>(input[offset + column]) /
                             denominator * static_cast<double>(gamma[gain_offset + column]);
            ideal[offset + column] = y;
            norm_squared += y * y;
            max_reference = std::max(max_reference, std::abs(y));
        }
    }
    Buffer x(count), gain(gamma.size()), output(count + 2 * guard_words);
    checked(cudaMemcpyAsync(x.data, input.data(), count * sizeof(float), cudaMemcpyHostToDevice, stream));
    checked(cudaMemcpyAsync(gain.data, gamma.data(), gamma.size() * sizeof(float), cudaMemcpyHostToDevice, stream));
    checked(cudaMemsetAsync(output.data, 0x5a, (count + 2 * guard_words) * sizeof(float), stream));
    strata::kernels::native_gr_rms_norm_weighted_multi(x.data, gain.data, output.data + guard_words,
                                                      columns, groups, tokens, epsilon, stream);
    checked(cudaStreamSynchronize(stream));
    std::vector<float> actual(count + 2 * guard_words), preserved_input(count), preserved_gamma(gamma.size());
    checked(cudaMemcpy(actual.data(), output.data, actual.size() * sizeof(float), cudaMemcpyDeviceToHost));
    checked(cudaMemcpy(preserved_input.data(), x.data, count * sizeof(float), cudaMemcpyDeviceToHost));
    checked(cudaMemcpy(preserved_gamma.data(), gain.data, gamma.size() * sizeof(float), cudaMemcpyDeviceToHost));
    if (std::memcmp(input.data(), preserved_input.data(), count * sizeof(float)) ||
        std::memcmp(gamma.data(), preserved_gamma.data(), gamma.size() * sizeof(float)))
        throw std::runtime_error("input or gamma mutation");
    for (std::size_t i = 0; i < actual.size(); ++i) {
        if (i >= guard_words && i < count + guard_words) continue;
        std::uint32_t bits;
        std::memcpy(&bits, &actual[i], sizeof(bits));
        if (bits != 0x5a5a5a5au) throw std::runtime_error("output guard mutation");
    }
    double error_squared = 0, max_error = 0;
    for (std::size_t i = 0; i < count; ++i) {
        if (!std::isfinite(actual[i + guard_words])) throw std::runtime_error("nonfinite output");
        const double error = std::abs(actual[i + guard_words] - ideal[i]);
        error_squared += error * error;
        max_error = std::max(max_error, error);
    }
    const double relative = norm_squared ? std::sqrt(error_squared / norm_squared) : std::sqrt(error_squared);
    std::printf("{\"columns\":%d,\"groups\":%d,\"tokens\":%d,\"mode\":%d,"
                "\"relative_l2\":%.17g,\"maximum_absolute_error\":%.17g,\"maximum_reference\":%.17g}\n",
                columns, groups, tokens, mode, relative, max_error, max_reference);
    if (relative > relative_l2_limit || max_error > absolute_floor + relative_max_limit * max_reference)
        throw std::runtime_error("predeclared numerical criterion failed");
}

template<class F> void must_reject(F&& operation) {
    try { operation(); } catch (const std::invalid_argument&) { return; }
    throw std::runtime_error("invalid arguments were not rejected before launch");
}

void invalid_cases() {
    Buffer x(128), gamma(128), output(128);
    auto launch = [&](const float* input, int columns, int rows, int tokens, float epsilon) {
        strata::kernels::native_gr_rms_norm_weighted_multi(input, gamma.data, output.data,
                                                          columns, rows, tokens, epsilon, nullptr);
    };
    must_reject([&] { launch(nullptr, 128, 1, 1, 1e-6f); });
    must_reject([&] { launch(x.data, 0, 1, 1, 1e-6f); });
    must_reject([&] { launch(x.data, 128, 0, 1, 1e-6f); });
    must_reject([&] { launch(x.data, 128, 1, 0, 1e-6f); });
    must_reject([&] { launch(x.data, 128, 1, 1, -1); });
    must_reject([&] { launch(x.data, 128, 1, 1, std::numeric_limits<float>::quiet_NaN()); });
    must_reject([&] { launch(x.data, 128, 1, 1, std::numeric_limits<float>::infinity()); });
    const auto unaligned = reinterpret_cast<float*>(reinterpret_cast<std::uint8_t*>(x.data) + 1);
    must_reject([&] { launch(unaligned, 128, 1, 1, 1e-6f); });
    std::puts("{\"invalid_argument_cases\":8,\"status\":\"pass\"}");
}
} // namespace

int main() {
    int devices = 0;
    if (cudaGetDeviceCount(&devices) != cudaSuccess || !devices) return 77;
    cudaStream_t stream = nullptr;
    try {
        invalid_cases();
        checked(cudaStreamCreate(&stream));
        for (int columns : {128, 1023, 1024, 1025, 2560, 10240}) {
            for (int mode : {0, 1, 2}) evaluate(columns, 4, 2, mode, stream);
            evaluate(columns, 1, 1, 0, nullptr);
        }
        evaluate(2560, 4, 64, 0, stream);
        checked(cudaStreamDestroy(stream));
        stream = nullptr;
        std::puts("{\"status\":\"pass\",\"oracle\":\"independent FP64 from represented F32 inputs\"}");
        return 0;
    } catch (const std::exception& error) {
        if (stream) cudaStreamDestroy(stream);
        std::fprintf(stderr, "FAIL: %s\n", error.what());
        return 1;
    }
}

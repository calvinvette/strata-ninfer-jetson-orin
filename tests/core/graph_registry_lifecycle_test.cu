#include "strata/core/graph.hpp"

#include <cuda_runtime.h>

#include <array>
#include <cstdio>
#include <string>

namespace {

__global__ void copy_one(const int* input, int* output) {
    if (threadIdx.x == 0 && blockIdx.x == 0) output[0] = input[0];
}

bool check(cudaError_t status, const char* operation) {
    if (status == cudaSuccess) return true;
    std::fprintf(stderr, "%s: %s\n", operation, cudaGetErrorString(status));
    return false;
}

bool capture_and_replay(strata::core::GraphRegistry& registry, cudaStream_t stream,
                        int* input, int* output,
                        const std::array<int, 3>& values, const char* label) {
    std::string err;
    const auto body = [&] { copy_one<<<1, 1, 0, stream>>>(input, output); };
    if (!registry.record(strata::core::LayerType::GDN, 1, body, err)) {
        std::fprintf(stderr, "%s capture: %s\n", label, err.c_str());
        return false;
    }
    if (registry.size() != 1 || registry.captures() != 1) {
        std::fprintf(stderr, "%s: expected one captured graph\n", label);
        return false;
    }

    // The key is already present, so another record request must not execute its body.
    int duplicate_body_calls = 0;
    if (!registry.record(strata::core::LayerType::GDN, 1,
                         [&] { ++duplicate_body_calls; }, err)) {
        std::fprintf(stderr, "%s duplicate record: %s\n", label, err.c_str());
        return false;
    }
    if (duplicate_body_calls != 0 || registry.captures() != 1) {
        std::fprintf(stderr, "%s: cached record unexpectedly recaptured\n", label);
        return false;
    }

    for (size_t i = 0; i < values.size(); ++i) {
        if (!check(cudaMemcpyAsync(input, &values[i], sizeof(int),
                                   cudaMemcpyHostToDevice, stream),
                   "cudaMemcpyAsync input")) return false;
        if (!registry.launch(strata::core::LayerType::GDN, 1, 5000, err)) {
            std::fprintf(stderr, "%s replay: %s\n", label, err.c_str());
            return false;
        }
        int actual = 0;
        if (!check(cudaMemcpy(&actual, output, sizeof(actual), cudaMemcpyDeviceToHost),
                   "cudaMemcpy output")) return false;
        if (actual != values[i]) {
            std::fprintf(stderr, "%s replay %zu: expected %d, got %d\n",
                         label, i, values[i], actual);
            return false;
        }
    }
    return true;
}

}  // namespace

int main() {
    cudaStream_t stream = nullptr;
    int* old_input = nullptr;
    int* old_output = nullptr;
    int* new_input = nullptr;
    int* new_output = nullptr;
    bool ok = check(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), "cudaStreamCreate");
    if (ok) ok = check(cudaMalloc(&old_input, sizeof(int)), "cudaMalloc old input");
    if (ok) ok = check(cudaMalloc(&old_output, sizeof(int)), "cudaMalloc old output");

    if (ok) {
        // Keep the old graph alive while the larger replacement buffers are allocated. This
        // models pool growth before retiring the graph that captured the old addresses.
        {
            strata::core::GraphRegistry old_registry(stream);
            ok = capture_and_replay(old_registry, stream, old_input, old_output,
                                    {11, -29, 104}, "initial graph");
            if (ok) ok = check(cudaMalloc(&new_input, 2 * sizeof(int)),
                               "cudaMalloc replacement input");
            if (ok) ok = check(cudaMalloc(&new_output, 2 * sizeof(int)),
                               "cudaMalloc replacement output");
            if (ok && (new_input == old_input || new_output == old_output)) {
                std::fprintf(stderr, "replacement allocation reused a still-live address\n");
                ok = false;
            }
        }  // Destroy the old executable graph before the next registry records its pointers.
    }

    // The caller, not GraphRegistry, owns the graph-before-buffer replacement contract.
    if (ok) {
        strata::core::GraphRegistry replacement_registry(stream);
        ok = capture_and_replay(replacement_registry, stream, new_input, new_output,
                                {7, 63, -512}, "replacement graph");
    }

    if (stream && !check(cudaStreamSynchronize(stream), "cudaStreamSynchronize cleanup")) ok = false;
    if (new_output && !check(cudaFree(new_output), "cudaFree replacement output")) ok = false;
    if (new_input && !check(cudaFree(new_input), "cudaFree replacement input")) ok = false;
    if (old_output && !check(cudaFree(old_output), "cudaFree old output")) ok = false;
    if (old_input && !check(cudaFree(old_input), "cudaFree old input")) ok = false;
    if (stream && !check(cudaStreamDestroy(stream), "cudaStreamDestroy")) ok = false;
    if (!ok) return 1;
    std::puts("graph registry stable-address replay and replacement recapture passed");
    return 0;
}

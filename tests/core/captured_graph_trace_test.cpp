#include "strata/core/graph.hpp"

#include <cuda_runtime.h>

#include <array>
#include <cstdio>
#include <string>

namespace {

bool check(cudaError_t status, const char* operation) {
    if (status == cudaSuccess) return true;
    std::fprintf(stderr, "%s: %s\n", operation, cudaGetErrorString(status));
    return false;
}

}  // namespace

int main() {
    int device = -1;
    if (!check(cudaGetDevice(&device), "cudaGetDevice")) return 1;

    cudaStream_t stream = nullptr;
    if (!check(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), "cudaStreamCreate")) return 1;

    unsigned char* device_data = nullptr;
    if (!check(cudaMalloc(&device_data, 64), "cudaMalloc")) {
        cudaStreamDestroy(stream);
        return 1;
    }

    std::string err;
    bool ok = true;
    {
        strata::core::CapturedGraph graph;
        ok = graph.begin(stream, err);
        if (!ok) std::fprintf(stderr, "CapturedGraph::begin: %s\n", err.c_str());

        if (ok) {
            const cudaError_t memset_status = cudaMemsetAsync(device_data, 0xa5, 64, stream);
            ok = check(memset_status, "captured cudaMemsetAsync");
        }

        if (ok) {
            ok = graph.end(stream, err);
            if (!ok) std::fprintf(stderr, "CapturedGraph::end: %s\n", err.c_str());
        }
        if (ok) {
            ok = graph.launch(stream, err);
            if (!ok) std::fprintf(stderr, "CapturedGraph::launch: %s\n", err.c_str());
        }
        if (ok && !graph.wait_ms(5000)) {
            std::fprintf(stderr, "CapturedGraph::wait_ms timed out or failed\n");
            ok = false;
        }

        std::array<unsigned char, 64> host_data{};
        if (ok) ok = check(cudaMemcpy(host_data.data(), device_data, host_data.size(),
                                      cudaMemcpyDeviceToHost), "cudaMemcpy result");
        for (unsigned char value : host_data) {
            if (value != 0xa5) {
                std::fprintf(stderr, "captured graph result mismatch: got 0x%02x\n", value);
                ok = false;
                break;
            }
        }
    }

    const bool cleanup_ok = check(cudaFree(device_data), "cudaFree") &&
                            check(cudaStreamDestroy(stream), "cudaStreamDestroy");
    if (!ok || !cleanup_ok) return 1;
    std::printf("captured graph replay passed on CUDA device %d\n", device);
    return 0;
}

#include "strata/core/graph.hpp"

#include <cuda_runtime.h>

#include <array>
#include <chrono>
#include <cstdlib>
#include <cstdio>
#include <string>
#include <thread>

namespace {

bool check(cudaError_t status, const char* operation) {
    if (status == cudaSuccess) return true;
    std::fprintf(stderr, "%s: %s\n", operation, cudaGetErrorString(status));
    return false;
}

void trace_pause(const char* marker) {
    const char* value = std::getenv("STRATA_CAPTURED_GRAPH_TRACE_PAUSE_MS");
    if (!value || !*value) return;
    char* end = nullptr;
    const long milliseconds = std::strtol(value, &end, 10);
    if (end == value || *end != '\0' || milliseconds <= 0 || milliseconds > 10000) return;
    const double now = std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    std::fprintf(stderr, "captured graph trace marker: {\"marker\":\"%s\",\"monotonic_s\":%.9f}\n",
                 marker, now);
    std::fflush(stderr);
    std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
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

    trace_pause("before_capture");
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
        if (ok) trace_pause("after_instantiate");
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

#include "strata/core/session.hpp"

#include <cuda_runtime.h>

#include <cstdio>
#include <string>

int main() {
    strata::core::SessionLoopScratch scratch;
    std::string error;
    constexpr size_t kBytes = 64u << 10;
    if (!scratch.init(kBytes, error)) {
        std::fprintf(stderr, "SessionLoopScratch::init: %s\n", error.c_str());
        return 1;
    }
    if (scratch.y_miss == nullptr || scratch.parts_bytes != kBytes || scratch.probe == nullptr) {
        std::fprintf(stderr, "SessionLoopScratch did not retain its requested owner state\n");
        scratch.free();
        return 1;
    }
    void* device_pointer = nullptr;
    if (cudaHostGetDevicePointer(&device_pointer, scratch.y_miss, 0) != cudaSuccess || device_pointer == nullptr) {
        std::fprintf(stderr, "SessionLoopScratch host allocation is not mapped\n");
        scratch.free();
        return 1;
    }
    scratch.free();
    if (scratch.y_miss != nullptr || scratch.parts_bytes != 0 || scratch.probe != nullptr) {
        std::fprintf(stderr, "SessionLoopScratch did not release its owner state\n");
        return 1;
    }
    scratch.free();  // idempotent teardown must not emit another release.
    std::puts("session loop scratch mapped-host lifecycle: PASS");
    return 0;
}

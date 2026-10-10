// Test-only LD_PRELOAD shim: refuse the 32 MiB CUDA prefill GEMM workspace once.
#include <cuda_runtime_api.h>
#include <dlfcn.h>
#include <execinfo.h>
#include <atomic>
#include <cstdio>

extern "C" cudaError_t cudaMalloc(void** ptr, size_t size) {
    using Malloc = cudaError_t (*)(void**, size_t);
    static auto real = reinterpret_cast<Malloc>(dlsym(RTLD_NEXT, "cudaMalloc"));
    static std::atomic<bool> refused{false};
    constexpr size_t kGemmWorkspaceBytes = (32u << 20) + 256u;
    if (size == kGemmWorkspaceBytes && !refused.exchange(true)) {
        *ptr = nullptr;
        std::fprintf(stderr, "TEST_SHIM: refused one %zu-byte CUDA GEMM workspace allocation\n", size);
        void* frames[16];
        const int n = backtrace(frames, 16);
        backtrace_symbols_fd(frames, n, 2);
        return cudaErrorMemoryAllocation;
    }
    if (real == nullptr) return cudaErrorUnknown;
    return real(ptr, size);
}

// Test-only LD_PRELOAD shim: refuse the first expert-stage-sized cudaHostAlloc.
// All other sizes and every later call go through to the real CUDA runtime.
#include <cuda_runtime_api.h>
#include <dlfcn.h>
#include <atomic>
#include <cstdio>
#include <execinfo.h>

extern "C" cudaError_t cudaHostAlloc(void** ptr, size_t size, unsigned int flags) {
    using HostAlloc = cudaError_t (*)(void**, size_t, unsigned int);
    static auto real = reinterpret_cast<HostAlloc>(dlsym(RTLD_NEXT, "cudaHostAlloc"));
    static std::atomic<unsigned> matching_calls{0};
    static std::atomic<bool> refused{false};
    // The default Stager ring creates sixteen 2,662,400-byte buffers first.
    // Refuse the next exact-size request, expected to be FileExpertSource staging.
    if (size == 2662400 && matching_calls.fetch_add(1) == 16 && !refused.exchange(true)) {
        *ptr = nullptr;
        std::fprintf(stderr, "TEST_SHIM: refused one %zu-byte cudaHostAlloc; caller stack follows\n", size);
        void* frames[16];
        const int n = backtrace(frames, 16);
        backtrace_symbols_fd(frames, n, 2);
        return cudaErrorMemoryAllocation;
    }
    if (real == nullptr) return cudaErrorUnknown;
    return real(ptr, size, flags);
}

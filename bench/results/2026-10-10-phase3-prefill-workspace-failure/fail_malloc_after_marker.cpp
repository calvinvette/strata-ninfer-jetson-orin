// Test-only LD_PRELOAD shim: refuse one CUDA allocation after a marker appears.
#include <cuda_runtime_api.h>
#include <dlfcn.h>
#include <execinfo.h>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <sys/stat.h>

extern "C" cudaError_t cudaMalloc(void** ptr, size_t size) {
    using Malloc = cudaError_t (*)(void**, size_t);
    static auto real = reinterpret_cast<Malloc>(dlsym(RTLD_NEXT, "cudaMalloc"));
    static std::atomic<bool> refused{false};
    const char* marker = std::getenv("STRATA_FAIL_ALLOC_MARKER");
    const char* min_text = std::getenv("STRATA_FAIL_ALLOC_MIN_BYTES");
    const size_t min_bytes = min_text ? std::strtoull(min_text, nullptr, 10) : (1u << 20);
    struct stat st {};
    if (marker && *marker && size >= min_bytes && stat(marker, &st) == 0 && !refused.exchange(true)) {
        *ptr = nullptr;
        std::fprintf(stderr, "TEST_SHIM: refused one post-marker cudaMalloc size=%zu marker=%s\n", size, marker);
        void* frames[20];
        const int n = backtrace(frames, 20);
        backtrace_symbols_fd(frames, n, 2);
        return cudaErrorMemoryAllocation;
    }
    if (real == nullptr) return cudaErrorUnknown;
    return real(ptr, size);
}

// Test-only CUDA runtime allocation probe. Emits process-local cudaMalloc and
// cudaMallocManaged live/high-water bytes; it does not account for graph execs,
// driver-internal memory, or allocations made through other APIs.
#include <cuda_runtime_api.h>
#include <dlfcn.h>
#include <unistd.h>

#include <cstdint>
#include <cstdio>
#include <mutex>
#include <unordered_map>

namespace {
thread_local bool in_probe = false;
std::mutex lock;
std::unordered_map<void*, size_t> live;
uint64_t current_bytes = 0, high_bytes = 0;

void event(const char* operation, void* ptr, size_t bytes, cudaError_t status,
           uint64_t current, uint64_t high) {
    std::fprintf(stderr,
        "CUDA_ALLOC_PROBE {\"pid\":%ld,\"op\":\"%s\",\"ptr\":\"%p\",\"bytes\":%zu,"
        "\"status\":%d,\"current_bytes\":%llu,\"high_bytes\":%llu}\n",
        static_cast<long>(getpid()), operation, ptr, bytes, static_cast<int>(status),
        static_cast<unsigned long long>(current), static_cast<unsigned long long>(high));
}

void allocated(const char* op, void* ptr, size_t bytes, cudaError_t status) {
    if (status != cudaSuccess || ptr == nullptr || in_probe) return;
    in_probe = true;
    uint64_t current, high;
    {
        std::lock_guard<std::mutex> guard(lock);
        live[ptr] = bytes;
        current_bytes += bytes;
        if (current_bytes > high_bytes) high_bytes = current_bytes;
        current = current_bytes;
        high = high_bytes;
    }
    event(op, ptr, bytes, status, current, high);
    in_probe = false;
}

void released(const char* op, void* ptr, cudaError_t status) {
    if (status != cudaSuccess || ptr == nullptr || in_probe) return;
    in_probe = true;
    size_t bytes = 0;
    uint64_t current, high;
    {
        std::lock_guard<std::mutex> guard(lock);
        auto it = live.find(ptr);
        if (it != live.end()) {
            bytes = it->second;
            current_bytes -= bytes;
            live.erase(it);
        }
        current = current_bytes;
        high = high_bytes;
    }
    event(op, ptr, bytes, status, current, high);
    in_probe = false;
}
}  // namespace

extern "C" cudaError_t CUDARTAPI cudaMalloc(void** ptr, size_t bytes) {
    using Fn = cudaError_t (CUDARTAPI *)(void**, size_t);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaMalloc"));
    if (!real) return cudaErrorUnknown;
    const auto status = real(ptr, bytes);
    allocated("malloc", status == cudaSuccess ? *ptr : nullptr, bytes, status);
    return status;
}

extern "C" cudaError_t CUDARTAPI cudaMallocManaged(void** ptr, size_t bytes,
                                                      unsigned int flags) {
    using Fn = cudaError_t (CUDARTAPI *)(void**, size_t, unsigned int);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaMallocManaged"));
    if (!real) return cudaErrorUnknown;
    const auto status = real(ptr, bytes, flags);
    allocated("malloc_managed", status == cudaSuccess ? *ptr : nullptr, bytes, status);
    return status;
}

extern "C" cudaError_t CUDARTAPI cudaFree(void* ptr) {
    using Fn = cudaError_t (CUDARTAPI *)(void*);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaFree"));
    if (!real) return cudaErrorUnknown;
    const auto status = real(ptr);
    released("free", ptr, status);
    return status;
}

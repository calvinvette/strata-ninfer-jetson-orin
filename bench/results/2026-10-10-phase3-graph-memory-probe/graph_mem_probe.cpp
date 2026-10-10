// Test-only CUDA interposer: sample graph async-pool attributes around instantiate.
#include <cuda_runtime_api.h>
#include <dlfcn.h>
#include <atomic>
#include <cstdint>
#include <cstdio>

namespace {
struct Snapshot { int device = -1; size_t free_bytes = 0, total_bytes = 0;
                  uint64_t used = 0, used_high = 0, reserved = 0, reserved_high = 0;
                  int status = 0; };
thread_local bool in_probe = false;
std::atomic<unsigned long long> sequence{0};

Snapshot snapshot() {
    Snapshot s;
    const bool was_in_probe = in_probe;
    in_probe = true;
    cudaError_t e = cudaGetDevice(&s.device);
    if (e == cudaSuccess) e = cudaMemGetInfo(&s.free_bytes, &s.total_bytes);
    if (e == cudaSuccess) e = cudaDeviceGetGraphMemAttribute(s.device, cudaGraphMemAttrUsedMemCurrent, &s.used);
    if (e == cudaSuccess) e = cudaDeviceGetGraphMemAttribute(s.device, cudaGraphMemAttrUsedMemHigh, &s.used_high);
    if (e == cudaSuccess) e = cudaDeviceGetGraphMemAttribute(s.device, cudaGraphMemAttrReservedMemCurrent, &s.reserved);
    if (e == cudaSuccess) e = cudaDeviceGetGraphMemAttribute(s.device, cudaGraphMemAttrReservedMemHigh, &s.reserved_high);
    s.status = static_cast<int>(e);
    in_probe = was_in_probe;
    return s;
}

void emit(unsigned long long id, const char* phase, const Snapshot& s, int instantiate_status) {
    std::fprintf(stderr,
        "GRAPH_MEM_PROBE {\"id\":%llu,\"phase\":\"%s\",\"device\":%d,\"free_bytes\":%zu,"
        "\"total_bytes\":%zu,\"graph_used_current_bytes\":%llu,\"graph_used_high_bytes\":%llu,"
        "\"graph_reserved_current_bytes\":%llu,\"graph_reserved_high_bytes\":%llu,"
        "\"query_status\":%d,\"operation_status\":%d}\n",
        id, phase, s.device, s.free_bytes, s.total_bytes,
        static_cast<unsigned long long>(s.used), static_cast<unsigned long long>(s.used_high),
        static_cast<unsigned long long>(s.reserved), static_cast<unsigned long long>(s.reserved_high),
        s.status, instantiate_status);
}

void emit_point(const char* phase, int status) {
    if (in_probe) return;
    const auto id = sequence.fetch_add(1, std::memory_order_relaxed) + 1;
    emit(id, phase, snapshot(), status);
}
}  // namespace

extern "C" cudaError_t CUDARTAPI cudaGraphInstantiate(cudaGraphExec_t* exec, cudaGraph_t graph,
                                                        unsigned long long flags) {
    using Fn = cudaError_t (CUDARTAPI *)(cudaGraphExec_t*, cudaGraph_t, unsigned long long);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaGraphInstantiate"));
    const auto id = sequence.fetch_add(1, std::memory_order_relaxed) + 1;
    emit(id, "before", snapshot(), -1);
    if (real == nullptr) return cudaErrorUnknown;
    const cudaError_t result = real(exec, graph, flags);
    emit(id, "after", snapshot(), static_cast<int>(result));
    return result;
}

extern "C" cudaError_t CUDARTAPI cudaGraphLaunch(cudaGraphExec_t exec, cudaStream_t stream) {
    using Fn = cudaError_t (CUDARTAPI *)(cudaGraphExec_t, cudaStream_t);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaGraphLaunch"));
    if (real == nullptr) return cudaErrorUnknown;
    const cudaError_t result = real(exec, stream);
    if (result == cudaSuccess) emit_point("after_graph_launch", static_cast<int>(result));
    return result;
}

extern "C" cudaError_t CUDARTAPI cudaStreamSynchronize(cudaStream_t stream) {
    using Fn = cudaError_t (CUDARTAPI *)(cudaStream_t);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaStreamSynchronize"));
    if (real == nullptr) return cudaErrorUnknown;
    const cudaError_t result = real(stream);
    if (result == cudaSuccess) emit_point("after_stream_synchronize", static_cast<int>(result));
    return result;
}

extern "C" cudaError_t CUDARTAPI cudaDeviceSynchronize() {
    using Fn = cudaError_t (CUDARTAPI *)();
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaDeviceSynchronize"));
    if (real == nullptr) return cudaErrorUnknown;
    const cudaError_t result = real();
    if (result == cudaSuccess) emit_point("after_device_synchronize", static_cast<int>(result));
    return result;
}

extern "C" cudaError_t CUDARTAPI cudaEventSynchronize(cudaEvent_t event) {
    using Fn = cudaError_t (CUDARTAPI *)(cudaEvent_t);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaEventSynchronize"));
    if (real == nullptr) return cudaErrorUnknown;
    const cudaError_t result = real(event);
    if (result == cudaSuccess) emit_point("after_event_synchronize", static_cast<int>(result));
    return result;
}

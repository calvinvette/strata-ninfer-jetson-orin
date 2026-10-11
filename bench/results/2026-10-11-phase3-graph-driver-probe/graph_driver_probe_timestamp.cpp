// Test-only CUDA Driver API allocation interposer for graph-instantiation probes.
// This reports allocations visible through public cuMemAlloc APIs only; it is not
// a complete inventory of driver-private graph executable resources.
#include <cuda.h>
#include <cuda_runtime_api.h>

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <dlfcn.h>
#include <mutex>
#include <unordered_map>

namespace {
double monotonic_now_s() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

std::atomic<unsigned> graph_instantiate_depth{0};
std::mutex allocation_mutex;
std::unordered_map<CUdeviceptr, size_t> graph_scoped_allocations;

void record_alloc(const char* api, CUdeviceptr ptr, size_t bytes, CUresult status) {
    const bool in_graph = graph_instantiate_depth.load(std::memory_order_relaxed) != 0;
    const bool trace_all = std::getenv("STRATA_GRAPH_DRIVER_TRACE_ALL") != nullptr;
    if (status != CUDA_SUCCESS || (!in_graph && !trace_all)) return;
    {
        std::lock_guard<std::mutex> lock(allocation_mutex);
        graph_scoped_allocations[ptr] = bytes;
    }
    std::fprintf(stderr,
                 "GRAPH_DRIVER_MEM {\"event\":\"alloc\",\"scope\":\"%s\",\"api\":\"%s\",\"ptr\":\"0x%llx\",\"bytes\":%zu}\n",
                 in_graph ? "instantiate" : "all", api, static_cast<unsigned long long>(ptr), bytes);
}

void record_free(CUdeviceptr ptr, CUresult status) {
    if (status != CUDA_SUCCESS) return;
    size_t bytes = 0;
    {
        std::lock_guard<std::mutex> lock(allocation_mutex);
        auto it = graph_scoped_allocations.find(ptr);
        if (it == graph_scoped_allocations.end()) return;
        bytes = it->second;
        graph_scoped_allocations.erase(it);
    }
    std::fprintf(stderr,
                 "GRAPH_DRIVER_MEM {\"event\":\"free\",\"ptr\":\"0x%llx\",\"bytes\":%zu}\n",
                 static_cast<unsigned long long>(ptr), bytes);
}
}  // namespace

extern "C" CUresult CUDAAPI cuMemAlloc_v2(CUdeviceptr* dptr, size_t bytes) {
    using Fn = CUresult(CUDAAPI*)(CUdeviceptr*, size_t);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cuMemAlloc_v2"));
    if (!real) return CUDA_ERROR_NOT_INITIALIZED;
    const CUresult result = real(dptr, bytes);
    if (std::getenv("STRATA_GRAPH_DRIVER_TRACE_ALL"))
        std::fprintf(stderr, "GRAPH_DRIVER_MEM {\"event\":\"alloc_call\",\"status\":%d,\"bytes\":%zu}\n",
                     static_cast<int>(result), bytes);
    if (dptr) record_alloc("cuMemAlloc_v2", *dptr, bytes, result);
    return result;
}

extern "C" CUresult CUDAAPI cuMemFree_v2(CUdeviceptr dptr) {
    using Fn = CUresult(CUDAAPI*)(CUdeviceptr);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cuMemFree_v2"));
    if (!real) return CUDA_ERROR_NOT_INITIALIZED;
    const CUresult result = real(dptr);
    record_free(dptr, result);
    return result;
}

extern "C" CUresult CUDAAPI cuMemAllocManaged(CUdeviceptr* dptr, size_t bytes, unsigned int flags) {
    using Fn = CUresult(CUDAAPI*)(CUdeviceptr*, size_t, unsigned int);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cuMemAllocManaged"));
    if (!real) return CUDA_ERROR_NOT_INITIALIZED;
    const CUresult result = real(dptr, bytes, flags);
    if (dptr) record_alloc("cuMemAllocManaged", *dptr, bytes, result);
    return result;
}

extern "C" CUresult CUDAAPI cuGraphInstantiate_v2(CUgraphExec* exec, CUgraph graph,
                                                    CUgraphNode* error_node, char* log_buffer,
                                                    size_t buffer_size) {
    using Fn = CUresult(CUDAAPI*)(CUgraphExec*, CUgraph, CUgraphNode*, char*, size_t);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cuGraphInstantiate_v2"));
    if (!real) return CUDA_ERROR_NOT_INITIALIZED;
    graph_instantiate_depth.fetch_add(1, std::memory_order_relaxed);
    const CUresult result = real(exec, graph, error_node, log_buffer, buffer_size);
    graph_instantiate_depth.fetch_sub(1, std::memory_order_relaxed);
    std::fprintf(stderr, "GRAPH_DRIVER_MEM {\"event\":\"instantiate\",\"api\":\"cuGraphInstantiate_v2\",\"status\":%d,\"monotonic_s\":%.6f}\n",
                 static_cast<int>(result), monotonic_now_s());
    return result;
}

extern "C" CUresult CUDAAPI cuGraphInstantiateWithFlags(CUgraphExec* exec, CUgraph graph,
                                                          unsigned long long flags) {
    using Fn = CUresult(CUDAAPI*)(CUgraphExec*, CUgraph, unsigned long long);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cuGraphInstantiateWithFlags"));
    if (!real) return CUDA_ERROR_NOT_INITIALIZED;
    graph_instantiate_depth.fetch_add(1, std::memory_order_relaxed);
    const CUresult result = real(exec, graph, flags);
    graph_instantiate_depth.fetch_sub(1, std::memory_order_relaxed);
    std::fprintf(stderr,
                 "GRAPH_DRIVER_MEM {\"event\":\"instantiate\",\"api\":\"cuGraphInstantiateWithFlags\",\"status\":%d,\"monotonic_s\":%.6f}\n",
                 static_cast<int>(result), monotonic_now_s());
    return result;
}

extern "C" cudaError_t CUDARTAPI cudaGraphInstantiate(cudaGraphExec_t* exec, cudaGraph_t graph,
                                                        unsigned long long flags) {
    using Fn = cudaError_t(CUDARTAPI*)(cudaGraphExec_t*, cudaGraph_t, unsigned long long);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaGraphInstantiate"));
    if (!real) return cudaErrorUnknown;
    graph_instantiate_depth.fetch_add(1, std::memory_order_relaxed);
    const cudaError_t result = real(exec, graph, flags);
    graph_instantiate_depth.fetch_sub(1, std::memory_order_relaxed);
    std::fprintf(stderr,
                 "GRAPH_DRIVER_MEM {\"event\":\"instantiate\",\"api\":\"cudaGraphInstantiate\",\"status\":%d,\"monotonic_s\":%.6f}\n",
                 static_cast<int>(result), monotonic_now_s());
    return result;
}

extern "C" cudaError_t CUDARTAPI cudaGraphInstantiateWithFlags(cudaGraphExec_t* exec, cudaGraph_t graph,
                                                                 unsigned long long flags) {
    using Fn = cudaError_t(CUDARTAPI*)(cudaGraphExec_t*, cudaGraph_t, unsigned long long);
    static auto real = reinterpret_cast<Fn>(dlsym(RTLD_NEXT, "cudaGraphInstantiateWithFlags"));
    if (!real) return cudaErrorUnknown;
    graph_instantiate_depth.fetch_add(1, std::memory_order_relaxed);
    const cudaError_t result = real(exec, graph, flags);
    graph_instantiate_depth.fetch_sub(1, std::memory_order_relaxed);
    std::fprintf(stderr,
                 "GRAPH_DRIVER_MEM {\"event\":\"instantiate\",\"api\":\"cudaGraphInstantiateWithFlags\",\"status\":%d,\"monotonic_s\":%.6f}\n",
                 static_cast<int>(result), monotonic_now_s());
    return result;
}

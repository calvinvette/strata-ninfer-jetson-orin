// Sequential ownership transfer diagnostic. Not an expert-cache or product-path benchmark.
#include <cuda_runtime.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <vector>

static void check(cudaError_t e, const char* what) {
    if (e != cudaSuccess) {
        std::fprintf(stderr, "%s: %s\n", what, cudaGetErrorString(e));
        std::exit(1);
    }
}

__global__ void sum_bytes(const unsigned char* p, size_t n, unsigned long long* result) {
    __shared__ unsigned long long sums[256];
    unsigned long long s = 0;
    for (size_t i = blockIdx.x * blockDim.x + threadIdx.x;
         i < n; i += size_t(gridDim.x) * blockDim.x) s += p[i];
    sums[threadIdx.x] = s;
    __syncthreads();
    for (int stride = 128; stride; stride /= 2) {
        if (threadIdx.x < stride) sums[threadIdx.x] += sums[threadIdx.x + stride];
        __syncthreads();
    }
    if (threadIdx.x == 0) atomicAdd(result, sums[0]);
}

int main() {
    constexpr size_t n = 64ull << 20;
    constexpr int iterations = 13;
    int device = 0;
    check(cudaSetDevice(device), "select device");
    cudaDeviceProp prop{};
    check(cudaGetDeviceProperties(&prop, device), "device properties");
    int concurrent_managed = 0;
    check(cudaDeviceGetAttribute(&concurrent_managed, cudaDevAttrConcurrentManagedAccess, device),
          "managed capability");
    std::printf("device=%s sm=%d.%d concurrentManagedAccess=%d bytes=%zu\n", prop.name,
                prop.major, prop.minor, concurrent_managed, n);

    unsigned long long* result = nullptr;
    check(cudaMalloc(&result, sizeof(*result)), "result allocation");
    cudaStream_t stream = nullptr;
    check(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), "stream create");
    cudaMemPool_t pool = nullptr;
    check(cudaDeviceGetDefaultMemPool(&pool, device), "default memory pool");
    uint64_t threshold = n;
    check(cudaMemPoolSetAttribute(pool, cudaMemPoolAttrReleaseThreshold, &threshold), "pool threshold");

    for (int mode = 0; mode < 4; ++mode) {
        unsigned char *host = nullptr, *gpu = nullptr;
        if (mode == 2) {
            check(cudaMallocManaged(&host, n), "managed allocation");
            gpu = host;
        } else {
            check(cudaHostAlloc(&host, n, cudaHostAllocMapped), "pinned host allocation");
            if (mode == 0) check(cudaMalloc(&gpu, n), "device allocation");
            else check(cudaHostGetDevicePointer(&gpu, host, 0), "mapped device pointer");
        }

        std::vector<double> timings;
        for (int iter = 0; iter < iterations; ++iter) {
            unsigned long long expected = 0;
            for (size_t i = 0; i < n; ++i) {
                host[i] = static_cast<unsigned char>((i + iter) % 251);
                expected += host[i];
            }
            auto start = std::chrono::steady_clock::now();
            if (mode == 3) {
                check(cudaMallocAsync(&gpu, n, stream), "async pool allocation");
                check(cudaMemcpyAsync(gpu, host, n, cudaMemcpyHostToDevice, stream), "async H2D");
                check(cudaMemsetAsync(result, 0, sizeof(*result), stream), "async result clear");
                sum_bytes<<<256, 256, 0, stream>>>(gpu, n, result);
                check(cudaGetLastError(), "async checksum launch");
                check(cudaFreeAsync(gpu, stream), "async pool free");
            } else {
                check(cudaMemset(result, 0, sizeof(*result)), "result clear");
                if (mode == 0) check(cudaMemcpy(gpu, host, n, cudaMemcpyHostToDevice), "pinned H2D");
                sum_bytes<<<256, 256>>>(gpu, n, result);
                check(cudaGetLastError(), "checksum launch");
            }
            check(cudaDeviceSynchronize(), "ownership handoff synchronize");
            unsigned long long got = 0;
            check(cudaMemcpy(&got, result, sizeof(got), cudaMemcpyDeviceToHost), "checksum readback");
            if (got != expected) {
                std::fprintf(stderr, "checksum mismatch in mode %d iteration %d\n", mode, iter);
                return 1;
            }
            if (iter >= 3)
                timings.push_back(std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() - start).count());
        }
        std::sort(timings.begin(), timings.end());
        const char* name = mode == 0 ? "pinned_copy" : mode == 1 ? "mapped_host" :
                           mode == 2 ? "managed_sequential" : "async_pool_copy";
        std::printf("%s iterations=10 median_ms=%.6f min_ms=%.6f max_ms=%.6f checksum=PASS\n",
                    name, (timings[4] + timings[5]) / 2, timings.front(), timings.back());
        if (mode == 3) {
            uint64_t used_high = 0, reserved_high = 0, used_current = 0;
            check(cudaMemPoolGetAttribute(pool, cudaMemPoolAttrUsedMemHigh, &used_high), "pool used high-water");
            check(cudaMemPoolGetAttribute(pool, cudaMemPoolAttrReservedMemHigh, &reserved_high),
                  "pool reserved high-water");
            check(cudaMemPoolGetAttribute(pool, cudaMemPoolAttrUsedMemCurrent, &used_current),
                  "pool current usage");
            std::printf("async_pool high_water_used_bytes=%llu high_water_reserved_bytes=%llu current_used_bytes=%llu\n",
                        static_cast<unsigned long long>(used_high),
                        static_cast<unsigned long long>(reserved_high),
                        static_cast<unsigned long long>(used_current));
        }
        if (mode == 2) check(cudaFree(host), "managed free");
        else {
            check(cudaFreeHost(host), "pinned free");
            if (mode == 0) check(cudaFree(gpu), "device free");
        }
    }
    check(cudaStreamDestroy(stream), "stream destroy");
    check(cudaFree(result), "result free");
    return 0;
}

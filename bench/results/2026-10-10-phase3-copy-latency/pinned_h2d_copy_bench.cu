// Test-only isolated pinned H2D copy timing. Not a Strata product-path benchmark.
#include <cuda_runtime.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <vector>

static void check(cudaError_t e, const char* where) {
    if (e != cudaSuccess) {
        std::fprintf(stderr, "%s: %s\n", where, cudaGetErrorString(e));
        std::exit(1);
    }
}

__global__ void checksum(const unsigned char* data, size_t n, unsigned long long* out) {
    __shared__ unsigned long long sums[256];
    unsigned long long sum = 0;
    for (size_t i = size_t(blockIdx.x) * blockDim.x + threadIdx.x;
         i < n; i += size_t(gridDim.x) * blockDim.x) sum += data[i];
    sums[threadIdx.x] = sum;
    __syncthreads();
    for (unsigned stride = 128; stride; stride >>= 1) {
        if (threadIdx.x < stride) sums[threadIdx.x] += sums[threadIdx.x + stride];
        __syncthreads();
    }
    if (threadIdx.x == 0) atomicAdd(out, sums[0]);
}

int main() {
    constexpr size_t bytes = 64ull << 20;
    constexpr int warmups = 5;
    constexpr int samples = 25;
    unsigned char* host = nullptr;
    unsigned char* device = nullptr;
    unsigned long long* result = nullptr;
    cudaStream_t stream{};
    cudaEvent_t begin{}, end{};
    check(cudaSetDevice(0), "select device");
    cudaDeviceProp prop{};
    check(cudaGetDeviceProperties(&prop, 0), "device properties");
    check(cudaHostAlloc(&host, bytes, cudaHostAllocDefault), "pinned host allocation");
    check(cudaMalloc(&device, bytes), "device allocation");
    check(cudaMalloc(&result, sizeof(*result)), "checksum allocation");
    check(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), "stream creation");
    check(cudaEventCreate(&begin), "start event");
    check(cudaEventCreate(&end), "stop event");
    unsigned long long expected = 0;
    for (size_t i = 0; i < bytes; ++i) {
        host[i] = static_cast<unsigned char>((i * 13 + 7) % 251);
        expected += host[i];
    }

    std::vector<float> ms;
    for (int i = 0; i < warmups + samples; ++i) {
        check(cudaEventRecord(begin, stream), "record start");
        check(cudaMemcpyAsync(device, host, bytes, cudaMemcpyHostToDevice, stream), "pinned H2D");
        check(cudaEventRecord(end, stream), "record stop");
        check(cudaEventSynchronize(end), "wait for copy");
        float elapsed = 0;
        check(cudaEventElapsedTime(&elapsed, begin, end), "copy event elapsed time");
        if (i >= warmups) ms.push_back(elapsed);
    }
    check(cudaMemsetAsync(result, 0, sizeof(*result), stream), "clear checksum");
    checksum<<<256, 256, 0, stream>>>(device, bytes, result);
    check(cudaGetLastError(), "checksum launch");
    unsigned long long got = 0;
    check(cudaMemcpyAsync(&got, result, sizeof(got), cudaMemcpyDeviceToHost, stream), "copy checksum");
    check(cudaStreamSynchronize(stream), "wait for checksum");
    if (got != expected) {
        std::fprintf(stderr, "checksum mismatch: expected=%llu got=%llu\n", expected, got);
        return 1;
    }
    std::sort(ms.begin(), ms.end());
    const double median = ms[ms.size() / 2];
    std::printf("device=%s sm=%d.%d bytes=%zu samples=%zu warmups=%d "
                "h2d_copy_median_ms=%.6f min_ms=%.6f max_ms=%.6f "
                "effective_GBps=%.3f checksum=PASS samples_ms=",
                prop.name, prop.major, prop.minor, bytes, ms.size(), warmups,
                median, ms.front(), ms.back(), double(bytes) / (median * 1.0e6));
    for (size_t i = 0; i < ms.size(); ++i)
        std::printf("%s%.6f", i ? "," : "", ms[i]);
    std::printf("\n");
    check(cudaEventDestroy(begin), "destroy start event");
    check(cudaEventDestroy(end), "destroy stop event");
    check(cudaStreamDestroy(stream), "destroy stream");
    check(cudaFree(result), "free checksum");
    check(cudaFree(device), "free device buffer");
    check(cudaFreeHost(host), "free pinned buffer");
    return 0;
}

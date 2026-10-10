#include <cuda_runtime.h>
#include <cstdio>
#include <cstdint>

__global__ void touch(unsigned char* p) { if (threadIdx.x == 0) p[0] = 7; }

int main() {
    cudaStream_t stream = nullptr;
    cudaGraph_t graph = nullptr;
    cudaGraphExec_t exec = nullptr;
    unsigned char* device_buffer = nullptr;
    if (cudaStreamCreate(&stream) != cudaSuccess) return 1;
    if (cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal) != cudaSuccess) return 2;
    if (cudaMallocAsync(&device_buffer, 4u << 20, stream) != cudaSuccess) return 3;
    touch<<<1, 1, 0, stream>>>(device_buffer);
    if (cudaFreeAsync(device_buffer, stream) != cudaSuccess) return 4;
    if (cudaStreamEndCapture(stream, &graph) != cudaSuccess) return 5;
    if (cudaGraphInstantiate(&exec, graph, 0) != cudaSuccess) return 6;
    if (cudaGraphLaunch(exec, stream) != cudaSuccess) return 7;
    if (cudaStreamSynchronize(stream) != cudaSuccess) return 8;
    uint64_t used = 0, reserved = 0;
    cudaDeviceGetGraphMemAttribute(0, cudaGraphMemAttrUsedMemCurrent, &used);
    cudaDeviceGetGraphMemAttribute(0, cudaGraphMemAttrReservedMemCurrent, &reserved);
    std::printf("calibration_after_launch used=%llu reserved=%llu\n",
                static_cast<unsigned long long>(used), static_cast<unsigned long long>(reserved));
    cudaGraphExecDestroy(exec);
    cudaGraphDestroy(graph);
    cudaStreamDestroy(stream);
    return 0;
}

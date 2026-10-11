#include <cuda.h>

#include <cstdio>

int main() {
    CUresult status = cuInit(0);
    CUdevice device{};
    CUcontext context{};
    CUdeviceptr allocation{};
    if (status == CUDA_SUCCESS) status = cuDeviceGet(&device, 0);
    if (status == CUDA_SUCCESS) status = cuCtxCreate(&context, 0, device);
    if (status == CUDA_SUCCESS) status = cuMemAlloc(&allocation, 2u << 20);
    if (status == CUDA_SUCCESS) status = cuMemFree(allocation);
    if (context) {
        const CUresult destroy_status = cuCtxDestroy(context);
        if (status == CUDA_SUCCESS) status = destroy_status;
    }
    std::printf("driver allocation calibration status=%d\n", static_cast<int>(status));
    return status == CUDA_SUCCESS ? 0 : 1;
}

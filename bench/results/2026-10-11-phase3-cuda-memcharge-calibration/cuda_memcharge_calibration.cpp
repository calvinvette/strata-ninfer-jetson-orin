#include <cuda.h>
#include <chrono>
#include <cstdio>
#include <thread>
#include <cstdint>
static void sample(const char* phase) {
  FILE* f=fopen("/proc/meminfo","r"); long long kb=0; char line[256];
  if(f){while(fgets(line,sizeof(line),f)) if(sscanf(line,"MemAvailable: %lld kB",&kb)==1) break; fclose(f);}
  size_t free_bytes=0,total_bytes=0; const CUresult mem_status=cuMemGetInfo(&free_bytes,&total_bytes);
  std::printf("phase=%s wall_ns=%lld memavailable_bytes=%lld cuMemGetInfo_status=%d free_bytes=%zu total_bytes=%zu\n",phase,
    (long long)std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(),kb*1024,(int)mem_status,free_bytes,total_bytes);
  fflush(stdout);
}
int main(){
 CUresult s=cuInit(0); CUdevice d{}; CUcontext c{}; CUdeviceptr p{};
 if(s==CUDA_SUCCESS)s=cuDeviceGet(&d,0); if(s==CUDA_SUCCESS)s=cuCtxCreate(&c,0,d);
 sample("before");
 std::this_thread::sleep_for(std::chrono::seconds(2));
 if(s==CUDA_SUCCESS)s=cuMemAlloc(&p,512ull<<20);
 if(s==CUDA_SUCCESS)s=cuMemsetD8(p,0x5a,512ull<<20);
 if(s==CUDA_SUCCESS)s=cuCtxSynchronize();
 if(s==CUDA_SUCCESS){sample("allocated_touched"); std::this_thread::sleep_for(std::chrono::seconds(8));}
 if(s==CUDA_SUCCESS)s=cuMemFree(p);
 if(s==CUDA_SUCCESS)s=cuCtxSynchronize();
 if(s==CUDA_SUCCESS){sample("freed"); std::this_thread::sleep_for(std::chrono::seconds(8));}
 if(c)cuCtxDestroy(c); std::printf("cuda_status=%d\n",(int)s); return s==CUDA_SUCCESS?0:1;
}

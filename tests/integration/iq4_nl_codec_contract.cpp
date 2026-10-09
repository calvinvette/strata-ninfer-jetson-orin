// Original integration diagnostic, not a copied NInfer test or kernel.
// IQ4_NL layout/codebook: pinned ggml 3cf03257 ggml-common.h / ggml-quants.c,
// MIT, Copyright (c) 2023-2026 The ggml authors; existing notices retained.
// Independent arithmetic/rounding oracle; no production half/BF16 helper used.
#include "strata/artifact/dequant.hpp"
#include "codec_oracle.hpp"
#include "strata/kernels/dequant_bf16.hpp"
#include <cuda_runtime.h>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace {
constexpr std::array<int,16> symbols{-127,-104,-83,-65,-49,-35,-22,-10,1,13,25,38,53,69,89,113};
constexpr int guard = 16;
void check(cudaError_t e) { if(e != cudaSuccess) throw std::runtime_error(cudaGetErrorString(e)); }
void require(bool ok, const char* message) { if(!ok) throw std::runtime_error(message); }
struct DeviceBytes {
    void* p = nullptr;
    explicit DeviceBytes(size_t n) { check(cudaMalloc(&p,n)); }
    ~DeviceBytes() { if(p) cudaFree(p); }
    DeviceBytes(const DeviceBytes&) = delete;
    DeviceBytes& operator=(const DeviceBytes&) = delete;
};
using codec_oracle::half_value;
using codec_oracle::nearest_bf16;
uint32_t fbits(float x) { uint32_t b; std::memcpy(&b,&x,4); return b; }

void evaluate(int rows, int cols, int row0, bool exhaustive, cudaStream_t stream) {
    const int blocks_per_row = cols/32;
    const size_t total_blocks = size_t(rows+row0)*blocks_per_row;
    std::vector<uint8_t> packed(total_blocks*18);
    constexpr uint16_t edge_scales[]{0,32768,1,0x8001,0x03ff,0x0400,0x3555,0x3c01,0xbe00,0x7bff,0xfbff};
    size_t index = 0;
    for(size_t b=0;b<total_blocks;++b) {
        uint16_t scale;
        if(exhaustive) {
            // All sign/exponent/fraction combinations except exponent31.
            const unsigned sign = index / (31*1024), magnitude = index % (31*1024);
            scale = uint16_t((sign<<15) | magnitude); ++index;
        } else scale = edge_scales[(b*7+b/blocks_per_row)%11];
        packed[b*18] = uint8_t(scale); packed[b*18+1] = uint8_t(scale>>8);
        for(int j=0;j<16;++j) {
            const unsigned lo = (j+b)%16, hi = (15-j+3*b)%16;
            packed[b*18+2+j] = uint8_t(lo | (hi<<4));
        }
    }
    const size_t n = size_t(rows)*cols;
    std::vector<float> ideal(n);
    std::vector<uint16_t> rounded(n);
    size_t cpu_checks=0;
    for(int r=0;r<rows;++r) for(int k=0;k<blocks_per_row;++k) {
        const size_t b = size_t(row0+r)*blocks_per_row+k;
        const uint16_t h = unsigned(packed[b*18]) + 256*unsigned(packed[b*18+1]);
        std::array<float,32> cpu;
        strata::dequantize_iq4_nl(packed.data()+b*18,cpu.data());
        for(int e=0;e<32;++e) {
            const unsigned byte = packed[b*18+2+e%16];
            const unsigned code = e < 16 ? byte%16 : byte/16;
            const double value = half_value(h)*symbols[code];
            const size_t dst = size_t(r)*cols+k*32+e;
            ideal[dst] = float(value); rounded[dst] = nearest_bf16(value);
            require(fbits(cpu[e]) == fbits(ideal[dst]), "CPU scalar codec mismatch");
            ++cpu_checks;
        }
    }
    DeviceBytes input(packed.size()), out_f((n+2*guard)*4), out_b((n+2*guard)*2);
    check(cudaMemcpyAsync(input.p,packed.data(),packed.size(),cudaMemcpyHostToDevice,stream));
    check(cudaMemsetAsync(out_f.p,0xa5,(n+2*guard)*4,stream));
    check(cudaMemsetAsync(out_b.p,0xa5,(n+2*guard)*2,stream));
    strata::kernels::dequant_f32(20,input.p,row0,rows,cols,static_cast<float*>(out_f.p)+guard,stream);
    strata::kernels::dequant_bf16(20,input.p,row0,rows,cols,static_cast<uint16_t*>(out_b.p)+guard,stream);
    check(cudaStreamSynchronize(stream));
    std::vector<float> got_f(n+2*guard);
    std::vector<uint16_t> got_b(n+2*guard);
    std::vector<uint8_t> retained(packed.size());
    check(cudaMemcpy(got_f.data(),out_f.p,got_f.size()*4,cudaMemcpyDeviceToHost));
    check(cudaMemcpy(got_b.data(),out_b.p,got_b.size()*2,cudaMemcpyDeviceToHost));
    check(cudaMemcpy(retained.data(),input.p,retained.size(),cudaMemcpyDeviceToHost));
    require(retained == packed, "packed input changed");
    for(size_t i=0;i<n;++i) {
        require(fbits(got_f[i+guard]) == fbits(ideal[i]), "GPU F32 codec mismatch");
        require(got_b[i+guard] == rounded[i], "GPU BF16 rounding mismatch");
    }
    for(int i=0;i<guard;++i) for(size_t pos : {size_t(i),n+guard+i}) {
        require(fbits(got_f[pos]) == 0xa5a5a5a5u, "F32 output guard changed");
        require(got_b[pos] == 0xa5a5u, "BF16 output guard changed");
    }
    std::printf("rows=%d cols=%d row0=%d exhaustive=%d: %zu CPU/F32/BF16 exact values, input/guards preserved\n",rows,cols,row0,exhaustive,cpu_checks);
}
}
int main() {
    int devices=0;
    if(cudaGetDeviceCount(&devices) != cudaSuccess || !devices) return 77;
    cudaStream_t stream=nullptr;
    try {
        require(half_value(1) == std::ldexp(1.0,-24), "half subnormal oracle anchor");
        require(half_value(0x3c00) == 1.0, "half unit oracle anchor");
        require(half_value(0x7bff) == 65504.0, "half maximum oracle anchor");
        require(nearest_bf16(1.0+1.0/256) == 0x3f80, "even lower BF16 tie anchor");
        require(nearest_bf16(1.0+3.0/256) == 0x3f82, "even upper BF16 tie anchor");
        require(nearest_bf16(-1.0-3.0/256) == 0xbf82, "negative BF16 tie anchor");
        require(nearest_bf16(-0.0) == 0x8000, "signed zero oracle anchor");
        check(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
        require(strata::kernels::dequant_bf16_supported(20), "IQ4_NL unsupported");
        // Exhaustive finite scales and all codes in both packed halves.
        evaluate(63488,32,0,true,stream);
        for(int cols : {32,256,288,640,2560,10240}) for(int rows : {1,3})
            evaluate(rows,cols,2,false,stream);
        // A full routed-expert down matrix in the verified artifact: [2560,640].
        evaluate(2560,640,3,false,stream);
        check(cudaStreamDestroy(stream)); stream=nullptr;
        std::puts("IQ4_NL independent codec contract: 14 cases PASS (finite scales only)");
        return 0;
    } catch(const std::exception& e) {
        std::fprintf(stderr,"IQ4_NL contract FAIL: %s\n",e.what());
        if(stream) cudaStreamDestroy(stream);
        return 1;
    }
}

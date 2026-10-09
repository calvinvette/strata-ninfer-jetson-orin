// Original integration test; no NInfer implementation copied.
// Q6_K format: ggml 3cf03257 ggml-common.h / ggml-quants.c (MIT, existing notices retained).
// Fixtures encode logical signed quants; the oracle never decodes the packed fields.
#include "codec_oracle.hpp"
#include "strata/artifact/dequant.hpp"
#include "strata/kernels/dequant_bf16.hpp"
#include <cuda_runtime.h>
#include <array>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace {
constexpr int guard=16;
void require(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
void check(cudaError_t e) { if(e!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(e)); }
struct DeviceBytes {
    void* p=nullptr;
    explicit DeviceBytes(size_t n) { check(cudaMalloc(&p,n)); }
    ~DeviceBytes() { if(p) cudaFree(p); }
    DeviceBytes(const DeviceBytes&)=delete;
    DeviceBytes& operator=(const DeviceBytes&)=delete;
};
uint32_t fbits(float x) { uint32_t b;std::memcpy(&b,&x,4);return b; }
using Quants=std::array<int,256>;
using Scales=std::array<int,16>;
using Block=std::array<uint8_t,210>;

Block encode(uint16_t d,const Quants& quant,const Scales& scales) {
    Block packed{};
    // Flat logical element -> mandated low/high field locations, no decoder call.
    for(unsigned e=0;e<256;++e) {
        require(quant[e]>=-32 && quant[e]<=31,"invalid fixture quant");
        const unsigned code=unsigned(quant[e]+32), half=e/128, quadrant=(e%128)/32, lane=e%32;
        const unsigned low_byte=half*64+(quadrant%2)*32+lane;
        const unsigned high_byte=128+half*32+lane;
        packed[low_byte] |= uint8_t((code%16) << (4*(quadrant/2)));
        packed[high_byte] |= uint8_t((code/16) << (2*quadrant));
    }
    for(unsigned g=0;g<16;++g) {
        require(scales[g]>=-128 && scales[g]<=127,"invalid fixture subscale");
        packed[192+g]=uint8_t(scales[g]);
    }
    packed[208]=uint8_t(d);packed[209]=uint8_t(d>>8);
    return packed;
}

void evaluate(int rows,int cols,int row0,int mode,cudaStream_t stream) {
    const int blocks_per_row=cols/256;
    const size_t total_blocks=size_t(rows+row0)*blocks_per_row,n=size_t(rows)*cols;
    std::vector<uint8_t> packed(total_blocks*210);
    std::vector<float> ideal(n);
    std::vector<uint16_t> bf16(n),fp16(n);
    constexpr uint16_t half_edges[]{0,0x8000,1,0x8001,0x03ff,0x0400,0x3555,0x3c01,0xbe00,0x7bff,0xfbff};
    constexpr int scale_edges[]{-128,-127,-64,-33,-1,0,1,2,3,7,31,63,64,95,126,127};
    for(size_t b=0;b<total_blocks;++b) {
        const uint16_t d=mode==0 ? uint16_t((b/(31*1024)<<15) | (b%(31*1024)))
                               : mode==1 ? 0x3c01 : half_edges[(7*b+b/blocks_per_row)%11];
        Quants quant;Scales scales;
        for(unsigned g=0;g<16;++g) {
            const size_t global_group=16*b+g;
            scales[g]=mode==1 ? int((global_group%256+128)%256)-128 : scale_edges[(g+b)%16];
        }
        for(unsigned e=0;e<256;++e) {
            const size_t global_group=16*b+e/16;
            quant[e]=mode==1 ? int(e%16+16*(global_group/256))-32
                             : int((13*e+17*b+7*(e/16))%64)-32;
        }
        const Block block=encode(d,quant,scales);
        std::memcpy(packed.data()+b*210,block.data(),210);
        if(b<size_t(row0)*blocks_per_row) continue;
        std::array<float,256> cpu;
        strata::dequantize_q6_K(block.data(),cpu.data());
        const size_t base=(b-size_t(row0)*blocks_per_row)*256;
        for(unsigned e=0;e<256;++e) {
            // Kept logical fixture data, not values unpacked by either implementation.
            const double value=codec_oracle::half_value(d)*double(scales[e/16])*double(quant[e]);
            ideal[base+e]=float(value);
            bf16[base+e]=codec_oracle::nearest_bf16(value);
            fp16[base+e]=codec_oracle::nearest_half(value);
            require(fbits(cpu[e])==fbits(ideal[base+e]),"CPU Q6_K mismatch");
        }
    }
    DeviceBytes input(packed.size()),out_f((n+2*guard)*4),out_b((n+2*guard)*2),out_h((n+2*guard)*2);
    check(cudaMemcpyAsync(input.p,packed.data(),packed.size(),cudaMemcpyHostToDevice,stream));
    check(cudaMemsetAsync(out_f.p,0xa5,(n+2*guard)*4,stream));
    check(cudaMemsetAsync(out_b.p,0xa5,(n+2*guard)*2,stream));
    check(cudaMemsetAsync(out_h.p,0xa5,(n+2*guard)*2,stream));
    strata::kernels::dequant_f32(14,input.p,row0,rows,cols,static_cast<float*>(out_f.p)+guard,stream);
    strata::kernels::dequant_bf16(14,input.p,row0,rows,cols,static_cast<uint16_t*>(out_b.p)+guard,stream);
    strata::kernels::dequant_f16(14,input.p,row0,rows,cols,static_cast<uint16_t*>(out_h.p)+guard,stream);
    check(cudaStreamSynchronize(stream));
    std::vector<float> got_f(n+2*guard);
    std::vector<uint16_t> got_b(n+2*guard),got_h(n+2*guard);
    std::vector<uint8_t> retained(packed.size());
    check(cudaMemcpy(got_f.data(),out_f.p,got_f.size()*4,cudaMemcpyDeviceToHost));
    check(cudaMemcpy(got_b.data(),out_b.p,got_b.size()*2,cudaMemcpyDeviceToHost));
    check(cudaMemcpy(got_h.data(),out_h.p,got_h.size()*2,cudaMemcpyDeviceToHost));
    check(cudaMemcpy(retained.data(),input.p,retained.size(),cudaMemcpyDeviceToHost));
    require(retained==packed,"packed input changed");
    for(size_t i=0;i<n;++i) {
        require(fbits(got_f[i+guard])==fbits(ideal[i]),"GPU F32 Q6_K mismatch");
        require(got_b[i+guard]==bf16[i],"GPU BF16 Q6_K rounding mismatch");
        require(got_h[i+guard]==fp16[i],"GPU FP16 Q6_K rounding mismatch");
    }
    for(int i=0;i<guard;++i) for(size_t pos : {size_t(i),n+guard+i}) {
        require(fbits(got_f[pos])==0xa5a5a5a5u,"F32 guard changed");
        require(got_b[pos]==0xa5a5u && got_h[pos]==0xa5a5u,"BF16/FP16 guard changed");
    }
    std::printf("rows=%d cols=%d row0=%d mode=%d: %zu CPU/F32/BF16/FP16 exact values, input/guards preserved\n",rows,cols,row0,mode,n);
    std::fflush(stdout);
}
}

int main() {
    int devices=0;
    if(cudaGetDeviceCount(&devices)!=cudaSuccess || !devices) return 77;
    cudaStream_t stream=nullptr;
    try {
        Quants zero{};Scales ones;ones.fill(1);
        const Block anchor=encode(0x3c00,zero,ones);
        for(unsigned i=0;i<128;++i) require(anchor[i]==0,"packed low-field anchor");
        for(unsigned i=128;i<192;++i) require(anchor[i]==0xaa,"packed high-field anchor");
        require(anchor[208]==0 && anchor[209]==0x3c,"scale placement anchor");
        require(codec_oracle::nearest_half(1.0+1.0/2048)==0x3c00,"FP16 even lower tie anchor");
        require(codec_oracle::nearest_half(1.0+3.0/2048)==0x3c02,"FP16 even upper tie anchor");
        require(codec_oracle::nearest_half(-0.0)==0x8000,"FP16 signed zero anchor");
        require(codec_oracle::nearest_half(65519.0)==0x7bff,"FP16 below overflow anchor");
        require(codec_oracle::nearest_half(65520.0)==0x7c00,"FP16 overflow tie anchor");
        check(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
        require(strata::kernels::dequant_bf16_supported(14),"Q6_K unsupported");
        evaluate(63488,256,0,0,stream);
        evaluate(1,16384,0,1,stream); // all 256 signed subscales x all 64 signed quant codes
        for(int cols : {256,512,768,2560,6144,10240}) for(int rows : {1,3})
            evaluate(rows,cols,2,2,stream);
        // Full synthetic GDN input matrix in the source inventory, [10240,2560].
        evaluate(10240,2560,1,2,stream);
        check(cudaStreamDestroy(stream));stream=nullptr;
        std::puts("Q6_K independent codec contract: 15 cases PASS (finite input scales; FP16 overflow follows IEEE)");
        return 0;
    } catch(const std::exception& e) {
        std::fprintf(stderr,"Q6_K contract FAIL: %s\n",e.what());
        if(stream) cudaStreamDestroy(stream);
        return 1;
    }
}

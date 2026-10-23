#include <cuda_runtime.h>
#include "strata/kernels/q8_1_finite.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

__global__ void replay(const float* gate, const float* up, float* hidden, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    const float g = gate[i];
#ifdef USE_RECIPROCAL
    const float sigmoid = 1.0f / (1.0f + expf(-g));
    hidden[i] = (g * sigmoid) * up[i];
#elif defined(USE_ACCURATE_EXP)
    hidden[i] = __fmul_rn(g / (1.0f + expf(-g)), up[i]);
#else
    hidden[i] = __fmul_rn(g / (1.0f + __expf(-g)), up[i]);
#endif
}

struct Q81Block { __half d, s; int8_t qs[32]; };
static_assert(sizeof(Q81Block) == 36, "Q8_1 block layout");

__global__ void quantize(const float* hidden, Q81Block* out, int n) {
    const int i = blockIdx.x * 32 + threadIdx.x;
    if (i >= n) return;
    const int lane = threadIdx.x & 31;
    float amax = fabsf(hidden[i]), sum = hidden[i];
#pragma unroll
    for (int offset = 16; offset > 0; offset >>= 1) {
        amax = fmaxf(amax, __shfl_xor_sync(0xffffffffu, amax, offset));
        sum += __shfl_xor_sync(0xffffffffu, sum, offset);
    }
    const float d = strata::kernels::q8_1_finite(amax / 127.0f);
    out[blockIdx.x].qs[lane] = strata::kernels::q8_1_quant(hidden[i], d, amax);
    if (lane == 0) {
        out[blockIdx.x].d = __float2half(strata::kernels::q8_1_finite(d));
        out[blockIdx.x].s = __float2half(strata::kernels::q8_1_finite(sum));
    }
}

static std::vector<float> read_f32(const char* path) {
    std::ifstream in(path, std::ios::binary);
    std::vector<char> bytes((std::istreambuf_iterator<char>(in)), {});
    if (!in && !in.eof()) throw std::runtime_error(std::string("read failed: ") + path);
    if (bytes.size() % sizeof(float)) throw std::runtime_error("input is not f32-aligned");
    std::vector<float> values(bytes.size() / sizeof(float));
    std::memcpy(values.data(), bytes.data(), bytes.size());
    return values;
}

int main(int argc, char** argv) {
    if (argc != 5) {
        std::fprintf(stderr, "usage: %s GATE.f32 UP.f32 OUTPUT.f32 OUTPUT.q8_1\n", argv[0]);
        return 2;
    }
    try {
        const auto gate = read_f32(argv[1]);
        const auto up = read_f32(argv[2]);
        if (gate.size() != up.size()) throw std::runtime_error("gate/up lengths differ");
        float *dg = nullptr, *du = nullptr, *dh = nullptr;
        Q81Block* dq = nullptr;
        const size_t bytes = gate.size() * sizeof(float);
        cudaMalloc(&dg, bytes); cudaMalloc(&du, bytes); cudaMalloc(&dh, bytes);
        cudaMalloc(&dq, gate.size() / 32 * sizeof(Q81Block));
        cudaMemcpy(dg, gate.data(), bytes, cudaMemcpyHostToDevice);
        cudaMemcpy(du, up.data(), bytes, cudaMemcpyHostToDevice);
        replay<<<(unsigned)((gate.size() + 255) / 256), 256>>>(dg, du, dh, (int)gate.size());
        quantize<<<(unsigned)(gate.size() / 32), 32>>>(dh, dq, (int)gate.size());
        cudaDeviceSynchronize();
        std::vector<float> hidden(gate.size());
        cudaMemcpy(hidden.data(), dh, bytes, cudaMemcpyDeviceToHost);
        std::ofstream out(argv[3], std::ios::binary);
        out.write(reinterpret_cast<const char*>(hidden.data()), (std::streamsize)bytes);
        if (!out) throw std::runtime_error("output write failed");
        std::vector<Q81Block> q8(gate.size() / 32);
        cudaMemcpy(q8.data(), dq, q8.size() * sizeof(Q81Block), cudaMemcpyDeviceToHost);
        std::ofstream qout(argv[4], std::ios::binary);
        qout.write(reinterpret_cast<const char*>(q8.data()), (std::streamsize)(q8.size() * sizeof(Q81Block)));
        if (!qout) throw std::runtime_error("Q8_1 output write failed");
        cudaFree(dg); cudaFree(du); cudaFree(dh); cudaFree(dq);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "replay: %s\n", e.what());
        return 1;
    }
}

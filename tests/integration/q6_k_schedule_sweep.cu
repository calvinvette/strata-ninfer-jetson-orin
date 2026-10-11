// Test-only Q6_K conversion CTA-size screen on the five real Orin profile shapes.
// The format math follows this repository's dequant_bf16.cu; no NInfer code is copied.
#include "strata/artifact/gguf_reader.hpp"
#include "strata/kernels/dequant_bf16.hpp"

#include <cuda_fp16.h>
#include <cuda_runtime.h>

#include <algorithm>
#include <array>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void check(cudaError_t e, const char* where) {
    if (e != cudaSuccess) throw std::runtime_error(std::string(where) + ": " + cudaGetErrorString(e));
}

struct DeviceBytes {
    void* p = nullptr;
    explicit DeviceBytes(size_t n) { check(cudaMalloc(&p, n), "cudaMalloc"); }
    ~DeviceBytes() { if (p) cudaFree(p); }
    DeviceBytes(const DeviceBytes&) = delete;
    DeviceBytes& operator=(const DeviceBytes&) = delete;
};

struct Shape {
    const char* name;
    int rows;
    int cols = 2560;
};

struct Sample {
    Shape shape;
    const uint8_t* source;
    DeviceBytes input;
    DeviceBytes baseline;
    DeviceBytes candidate;
    size_t input_bytes;
    size_t elements;
    int64_t row_bytes;

    Sample(const strata::GgufFile& file, Shape s)
        : shape(s), source(nullptr), input((size_t)s.rows * (size_t)(s.cols / 256) * 210),
          baseline((size_t)s.rows * (size_t)s.cols * 2), candidate((size_t)s.rows * (size_t)s.cols * 2),
          input_bytes((size_t)s.rows * (size_t)(s.cols / 256) * 210),
          elements((size_t)s.rows * (size_t)s.cols), row_bytes((s.cols / 256) * 210) {
        const strata::TensorInfo* t = file.find(s.name);
        if (!t || t->type != 14 || t->shape.size() != 2 || (int64_t)t->shape[0] != s.cols ||
            (int64_t)t->shape[1] != s.rows)
            throw std::runtime_error(std::string("unexpected Q6_K tensor: ") + s.name);
        source = file.tensor_data(*t);
    }
};

template <int THREADS>
__global__ void q6k_to_h16_candidate(const uint8_t* __restrict__ input, int64_t row_bytes, int rows, int cols,
                                     uint16_t* __restrict__ output) {
    const int64_t groups_per_row = cols / 32;
    const int64_t g = (int64_t)blockIdx.x * THREADS + threadIdx.x;
    if (g >= (int64_t)rows * groups_per_row) return;
    const int64_t r = g / groups_per_row;
    const int gi = (int)(g % groups_per_row);
    const int gi_k = gi % 8;
    const uint8_t* b = input + r * row_bytes + (size_t)(gi / 8) * 210;
    const int half = gi_k / 4;
    const int role = gi_k % 4;
    const uint8_t* ql = b + 64 * half;
    const uint8_t* qh = b + 128 + 32 * half;
    const int8_t* sc = (const int8_t*)(b + 192) + 8 * half;
    const float d = __half2float(*reinterpret_cast<const __half*>(b + 208));
    const int scale_lane = role * 2;
    for (int l = 0; l < 32; ++l) {
        const int is = l / 16;
        int q;
        if (role == 0) q = (ql[l] & 0x0f) | (((qh[l] >> 0) & 3) << 4);
        else if (role == 1) q = (ql[l + 32] & 0x0f) | (((qh[l] >> 2) & 3) << 4);
        else if (role == 2) q = (ql[l] >> 4) | (((qh[l] >> 4) & 3) << 4);
        else q = (ql[l + 32] >> 4) | (((qh[l] >> 6) & 3) << 4);
        const float value = d * (float)sc[is + scale_lane] * (float)(q - 32);
        output[r * cols + (int64_t)gi * 32 + l] = __half_as_ushort(__float2half_rn(value));
    }
}

void launch_baseline(Sample& s, cudaStream_t stream) {
    strata::kernels::dequant_f16(14, s.input.p, 0, s.shape.rows, s.shape.cols, (uint16_t*)s.baseline.p, stream);
}
template <int THREADS>
void launch_candidate(Sample& s, cudaStream_t stream) {
    const int64_t groups = (int64_t)s.shape.rows * (s.shape.cols / 32);
    const unsigned grid = (unsigned)((groups + THREADS - 1) / THREADS);
    q6k_to_h16_candidate<THREADS><<<grid, THREADS, 0, stream>>>(
        (const uint8_t*)s.input.p, s.row_bytes, s.shape.rows, s.shape.cols, (uint16_t*)s.candidate.p);
    check(cudaGetLastError(), "launch candidate");
}

using Launch = void (*)(Sample&, cudaStream_t);
struct Arm { const char* name; Launch launch; };
void prod(Sample& s, cudaStream_t st) { launch_baseline(s, st); }
void b128(Sample& s, cudaStream_t st) { launch_candidate<128>(s, st); }
void b256(Sample& s, cudaStream_t st) { launch_candidate<256>(s, st); }
void b512(Sample& s, cudaStream_t st) { launch_candidate<512>(s, st); }
constexpr std::array<Arm, 4> arms{{{"prod256", prod}, {"candidate128", b128}, {"candidate256", b256}, {"candidate512", b512}}};
constexpr int warmups = 5;
constexpr int launches_per_sample = 20;
constexpr int blocks = 7;

double time_batch(Sample& s, const Arm& arm, cudaStream_t stream, cudaEvent_t start, cudaEvent_t stop) {
    check(cudaEventRecord(start, stream), "record start");
    for (int i = 0; i < launches_per_sample; ++i) arm.launch(s, stream);
    check(cudaEventRecord(stop, stream), "record stop");
    check(cudaEventSynchronize(stop), "wait timed batch");
    float ms = 0;
    check(cudaEventElapsedTime(&ms, start, stop), "elapsed time");
    return (double)ms / launches_per_sample;
}

void verify_all(Sample& s, cudaStream_t stream) {
    launch_baseline(s, stream);
    check(cudaStreamSynchronize(stream), "baseline sync");
    std::vector<uint16_t> expected(s.elements), actual(s.elements);
    check(cudaMemcpy(expected.data(), s.baseline.p, s.elements * 2, cudaMemcpyDeviceToHost), "read baseline output");
    for (size_t a = 1; a < arms.size(); ++a) {
        arms[a].launch(s, stream);
        check(cudaStreamSynchronize(stream), "candidate sync");
        check(cudaMemcpy(actual.data(), s.candidate.p, s.elements * 2, cudaMemcpyDeviceToHost), "read candidate output");
        if (std::memcmp(expected.data(), actual.data(), s.elements * 2) != 0)
            throw std::runtime_error(std::string(arms[a].name) + " output differs from production for " + s.shape.name);
    }
    std::printf("exact-output,%s,%zu values,all schedules bit-identical\n", s.shape.name, s.elements);
}
}  // namespace

int main(int argc, char** argv) {
    if (argc != 2 && argc != 3) {
        std::fprintf(stderr, "usage: q6_k_schedule_sweep SHARD.gguf [ORDER_SEED]\n");
        return 2;
    }
    int devices = 0;
    if (cudaGetDeviceCount(&devices) != cudaSuccess || devices == 0) return 77;
    cudaStream_t stream = nullptr;
    cudaEvent_t start = nullptr, stop = nullptr;
    try {
        strata::GgufFile file(argv[1]);
        constexpr std::array<Shape, 5> shapes{{
            {"blk.1.attn_gate.weight", 6144}, {"blk.2.ffn_up_shexp.weight", 640},
            {"blk.0.attn_qkv.weight", 10240}, {"blk.3.attn_k.weight", 512}, {"blk.31.attn_q.weight", 12288},
        }};
        std::vector<std::unique_ptr<Sample>> samples;
        for (Shape s : shapes) samples.emplace_back(std::make_unique<Sample>(file, s));
        for (auto& s : samples) check(cudaMemcpy(s->input.p, s->source, s->input_bytes, cudaMemcpyHostToDevice), "copy source tensor");
        check(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), "create stream");
        check(cudaEventCreate(&start), "create start event");
        check(cudaEventCreate(&stop), "create stop event");

        for (auto& s : samples) {
            for (const Arm& arm : arms)
                for (int i = 0; i < warmups; ++i) arm.launch(*s, stream);
            check(cudaStreamSynchronize(stream), "warmup sync");
            verify_all(*s, stream);
        }

        std::array<std::array<std::array<double, arms.size()>, shapes.size()>, blocks> times{};
        const uint32_t seed = argc == 3 ? (uint32_t)std::strtoul(argv[2], nullptr, 10) : 20261011u;
        std::mt19937 rng(seed);
        for (int b = 0; b < blocks; ++b) {
            std::array<size_t, shapes.size()> shape_order{{0, 1, 2, 3, 4}};
            std::shuffle(shape_order.begin(), shape_order.end(), rng);
            for (size_t si : shape_order) {
                std::array<size_t, arms.size()> arm_order{{0, 1, 2, 3}};
                std::shuffle(arm_order.begin(), arm_order.end(), rng);
                std::printf("order,%d,%s", b, samples[si]->shape.name);
                for (size_t ai : arm_order) std::printf(",%s", arms[ai].name);
                std::putchar('\n');
                for (size_t ai : arm_order)
                    times[b][si][ai] = time_batch(*samples[si], arms[ai], stream, start, stop);
            }
        }
        std::printf("median_table,seed=%u,blocks=%d,launches_per_sample=%d\n", seed, blocks, launches_per_sample);
        std::puts("tensor,schedule,median_ms_per_launch,min_ms,max_ms,paired_delta_pct_vs_prod256");
        for (size_t si = 0; si < shapes.size(); ++si) {
            for (size_t ai = 0; ai < arms.size(); ++ai) {
                std::array<double, blocks> v{};
                for (int b = 0; b < blocks; ++b) v[(size_t)b] = times[(size_t)b][si][ai];
                auto sorted = v;
                std::sort(sorted.begin(), sorted.end());
                double delta = 0;
                if (ai != 0) {
                    std::array<double, blocks> d{};
                    for (int b = 0; b < blocks; ++b)
                        d[(size_t)b] = (times[(size_t)b][si][ai] / times[(size_t)b][si][0] - 1.0) * 100.0;
                    std::sort(d.begin(), d.end());
                    delta = d[blocks / 2];
                }
                std::printf("%s,%s,%.6f,%.6f,%.6f,%.3f\n", samples[si]->shape.name, arms[ai].name,
                            sorted[blocks / 2], sorted.front(), sorted.back(), delta);
                std::printf("raw_block_means_ms,%s,%s", samples[si]->shape.name, arms[ai].name);
                for (double t : v) std::printf(",%.6f", t);
                std::putchar('\n');
            }
        }
        check(cudaEventDestroy(stop), "destroy stop event");
        check(cudaEventDestroy(start), "destroy start event");
        check(cudaStreamDestroy(stream), "destroy stream");
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "Q6_K schedule sweep FAIL: %s\n", e.what());
        if (stop) cudaEventDestroy(stop);
        if (start) cudaEventDestroy(start);
        if (stream) cudaStreamDestroy(stream);
        return 1;
    }
}

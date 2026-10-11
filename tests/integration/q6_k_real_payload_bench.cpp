// Timed diagnostic for the real-shape Q6_K -> FP16 path on Orin.
// Original test code; it does not copy NInfer code or alter production dispatch.
#include "strata/artifact/gguf_reader.hpp"
#include "strata/kernels/dequant_bf16.hpp"

#include <cuda_runtime.h>

#include <algorithm>
#include <array>
#include <cstdio>
#include <memory>
#include <numeric>
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

struct Sample {
    const char* name;
    int64_t cols;
    int64_t rows;
    const uint8_t* source;
    DeviceBytes input;
    DeviceBytes output;
    size_t elements;
    size_t input_bytes;

    Sample(const strata::GgufFile& file, const char* tensor, int64_t nrows, int64_t ncols)
        : name(tensor), cols(ncols), rows(nrows), source(nullptr),
          input((size_t)nrows * (size_t)(ncols / 256) * 210),
          output((size_t)nrows * (size_t)ncols * sizeof(uint16_t)),
          elements((size_t)nrows * (size_t)ncols), input_bytes((size_t)nrows * (size_t)(ncols / 256) * 210) {
        const strata::TensorInfo* t = file.find(tensor);
        if (!t || t->type != 14 || t->shape.size() != 2 || (int64_t)t->shape[0] != ncols ||
            (int64_t)t->shape[1] != nrows)
            throw std::runtime_error(std::string("missing or unexpected Q6_K tensor: ") + tensor);
        source = file.tensor_data(*t);
    }
};

constexpr std::array<const char*, 5> names{{
    "blk.1.attn_gate.weight", "blk.2.ffn_up_shexp.weight", "blk.0.attn_qkv.weight",
    "blk.3.attn_k.weight", "blk.31.attn_q.weight",
}};
constexpr std::array<int64_t, 5> matrix_rows{{6144, 640, 10240, 512, 12288}};
constexpr int64_t matrix_cols = 2560;
constexpr int warmups = 5;
constexpr int launches_per_sample = 20;
constexpr int blocks = 7;

double time_batch(Sample& s, cudaStream_t stream, cudaEvent_t start, cudaEvent_t stop) {
    check(cudaEventRecord(start, stream), "record start");
    for (int i = 0; i < launches_per_sample; ++i)
        strata::kernels::dequant_f16(14, s.input.p, 0, s.rows, s.cols, (uint16_t*)s.output.p, stream);
    check(cudaEventRecord(stop, stream), "record stop");
    check(cudaEventSynchronize(stop), "wait for timed batch");
    float ms = 0;
    check(cudaEventElapsedTime(&ms, start, stop), "elapsed time");
    return (double)ms / launches_per_sample;
}
}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: q6_k_real_payload_bench SHARD.gguf\n");
        return 2;
    }
    int devices = 0;
    if (cudaGetDeviceCount(&devices) != cudaSuccess || devices == 0) return 77;
    cudaStream_t stream = nullptr;
    cudaEvent_t start = nullptr, stop = nullptr;
    try {
        strata::GgufFile file(argv[1]);
        std::vector<std::unique_ptr<Sample>> samples;
        for (size_t i = 0; i < names.size(); ++i)
            samples.emplace_back(std::make_unique<Sample>(file, names[i], matrix_rows[i], matrix_cols));

        for (auto& s : samples) check(cudaMemcpy(s->input.p, s->source, s->input_bytes, cudaMemcpyHostToDevice), "upload Q6_K tensor");
        check(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), "create stream");
        check(cudaEventCreate(&start), "create start event");
        check(cudaEventCreate(&stop), "create stop event");
        for (auto& s : samples) {
            for (int i = 0; i < warmups; ++i)
                strata::kernels::dequant_f16(14, s->input.p, 0, s->rows, s->cols, (uint16_t*)s->output.p, stream);
        }
        check(cudaStreamSynchronize(stream), "finish warmup");

        std::array<std::vector<double>, names.size()> ms;
        std::mt19937 rng(20261010);
        for (int b = 0; b < blocks; ++b) {
            std::array<size_t, names.size()> order{{0, 1, 2, 3, 4}};
            std::shuffle(order.begin(), order.end(), rng);
            std::printf("block_order,%d", b);
            for (size_t i : order) std::printf(",%s", samples[i]->name);
            std::putchar('\n');
            for (size_t i : order) ms[i].push_back(time_batch(*samples[i], stream, start, stop));
        }

        std::puts("scope=isolated warmed full-matrix Q6_K->FP16; batch=20 launches; blocks=7; order_seed=20261010");
        std::puts("tensor,matrix_rows,matrix_cols,input_MiB,output_MiB,median_ms_per_launch,min_ms,max_ms,effective_GB_s");
        for (size_t i = 0; i < samples.size(); ++i) {
            auto sorted = ms[i];
            std::sort(sorted.begin(), sorted.end());
            const double median = sorted[sorted.size() / 2];
            const double traffic = (double)samples[i]->input_bytes + (double)samples[i]->elements * 2.0;
            const double gbps = traffic / (median * 1.0e6);
            std::printf("%s,%lld,%lld,%.3f,%.3f,%.6f,%.6f,%.6f,%.3f\n", samples[i]->name,
                        (long long)samples[i]->rows, (long long)samples[i]->cols,
                        (double)samples[i]->input_bytes / 1048576.0,
                        (double)samples[i]->elements * 2.0 / 1048576.0,
                        median, sorted.front(), sorted.back(), gbps);
            std::printf("raw_block_means_ms,%s", samples[i]->name);
            for (double value : ms[i]) std::printf(",%.6f", value);
            std::putchar('\n');
        }
        check(cudaEventDestroy(stop), "destroy stop event");
        check(cudaEventDestroy(start), "destroy start event");
        check(cudaStreamDestroy(stream), "destroy stream");
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "Q6_K real-payload benchmark FAIL: %s\n", e.what());
        if (stop) cudaEventDestroy(stop);
        if (start) cudaEventDestroy(start);
        if (stream) cudaStreamDestroy(stream);
        return 1;
    }
}

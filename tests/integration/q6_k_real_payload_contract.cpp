// Real-payload Q6_K materialization diagnostic for the shapes seen in the Orin request trace.
// This is original test code; no NInfer implementation is used or copied.
#include "codec_oracle.hpp"
#include "strata/artifact/dequant.hpp"
#include "strata/artifact/gguf_reader.hpp"
#include "strata/kernels/dequant_bf16.hpp"

#include <cuda_runtime.h>

#include <array>
#include <cstdio>
#include <cstring>
#include <memory>
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

struct Case {
    const char* name;
    int64_t cols;
    int64_t rows;
};

constexpr std::array<Case, 5> cases{{
    {"blk.1.attn_gate.weight", 2560, 6144},
    {"blk.2.ffn_up_shexp.weight", 2560, 640},
    {"blk.0.attn_qkv.weight", 2560, 10240},
    {"blk.3.attn_k.weight", 2560, 512},
    {"blk.31.attn_q.weight", 2560, 12288},
}};

bool check_tensor(const strata::GgufFile& file, const Case& c) {
    const strata::TensorInfo* t = file.find(c.name);
    if (!t) return false;
    if (t->type != 14 || t->shape.size() != 2 || (int64_t)t->shape[0] != c.cols ||
        (int64_t)t->shape[1] != c.rows)
        throw std::runtime_error(std::string("unexpected source type/shape for ") + c.name);

    constexpr int rows = 4;
    const size_t row_bytes = (size_t)(c.cols / 256) * 210;
    const size_t input_bytes = rows * row_bytes;
    const size_t count = (size_t)rows * c.cols;
    const uint8_t* source = file.tensor_data(*t);
    DeviceBytes input(input_bytes), output(count * sizeof(uint16_t));
    check(cudaMemcpy(input.p, source, input_bytes, cudaMemcpyHostToDevice), "copy real Q6_K payload");
    strata::kernels::dequant_f16(14, input.p, 0, rows, c.cols, (uint16_t*)output.p, nullptr);
    check(cudaDeviceSynchronize(), "run Q6_K FP16 materializer");

    std::vector<uint16_t> actual(count);
    std::vector<uint8_t> retained(input_bytes);
    check(cudaMemcpy(actual.data(), output.p, count * sizeof(uint16_t), cudaMemcpyDeviceToHost), "read FP16 output");
    check(cudaMemcpy(retained.data(), input.p, input_bytes, cudaMemcpyDeviceToHost), "read source payload back");
    if (std::memcmp(retained.data(), source, input_bytes) != 0)
        throw std::runtime_error(std::string("input payload changed for ") + c.name);

    std::array<float, 256> block_values{};
    for (int64_t r = 0; r < rows; ++r) {
        const uint8_t* row = source + (size_t)r * row_bytes;
        for (int64_t b = 0; b < c.cols / 256; ++b) {
            strata::dequantize_q6_K(row + (size_t)b * 210, block_values.data());
            for (int j = 0; j < 256; ++j) {
                const size_t i = (size_t)r * c.cols + (size_t)b * 256 + j;
                const uint16_t expected = codec_oracle::nearest_half((double)block_values[(size_t)j]);
                if (actual[i] != expected)
                    throw std::runtime_error(std::string("FP16 value mismatch for ") + c.name +
                                             " at flattened index " + std::to_string(i));
            }
        }
    }
    std::printf("%s [%lld,%lld]: %zu real payload values, FP16 exact; source preserved\n", c.name,
                (long long)c.rows, (long long)c.cols, count);
    return true;
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: q6_k_real_payload_contract SHARD.gguf [SHARD2.gguf]\n");
        return 2;
    }
    int devices = 0;
    if (cudaGetDeviceCount(&devices) != cudaSuccess || devices == 0) return 77;
    try {
        std::vector<std::unique_ptr<strata::GgufFile>> shards;
        for (int i = 1; i < argc; ++i) shards.emplace_back(std::make_unique<strata::GgufFile>(argv[i]));
        size_t total = 0;
        for (const Case& c : cases) {
            bool found = false;
            for (const auto& shard : shards) {
                if (check_tensor(*shard, c)) {
                    found = true;
                    ++total;
                    break;
                }
            }
            if (!found) throw std::runtime_error(std::string("required tensor missing: ") + c.name);
        }
        std::printf("Q6_K real-payload FP16 contract: %zu shapes PASS\n", total);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "Q6_K real-payload FP16 contract FAIL: %s\n", e.what());
        return 1;
    }
}

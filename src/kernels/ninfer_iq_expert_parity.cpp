#include "strata/artifact/gguf_reader.hpp"
#include "strata/kernels/iq_kernels.hpp"
#include "strata/kernels/native_mmvq.hpp"
#include "strata/kernels/ninfer_iq_expert.hpp"

#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
constexpr int kHidden = 2560;
constexpr int kIntermediate = 640;
void check(cudaError_t e, const char* what) {
    if (e != cudaSuccess) throw std::runtime_error(std::string(what) + ": " + cudaGetErrorString(e));
}
std::vector<float> read_f32(const std::string& path, size_t count) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open " + path);
    std::vector<float> v(count);
    f.read(reinterpret_cast<char*>(v.data()), static_cast<std::streamsize>(count * sizeof(float)));
    if (f.gcount() != static_cast<std::streamsize>(count * sizeof(float)) || f.peek() != EOF)
        throw std::runtime_error("wrong byte count in " + path);
    return v;
}
}

int main(int argc, char** argv) {
    if (argc != 5) {
        std::fprintf(stderr, "usage: ninfer_iq_expert_parity shard-00001.gguf layer expert activation.f32\n");
        return 2;
    }
    try {
        const int layer = std::stoi(argv[2]);
        const int expert = std::stoi(argv[3]);
        if (layer < 0 || layer >= 48 || expert < 0)
            throw std::invalid_argument("layer/expert outside model bounds");
        auto model = strata::GgufModel::open(argv[1]);
        const std::string prefix = "blk." + std::to_string(layer) + ".ffn_";
        size_t shard = 0;
        const auto* gate = model.find(prefix + "gate_exps.weight", &shard);
        if (!gate || (gate->type != 22 && gate->type != 18 && gate->type != 21) ||
            gate->shape.size() != 3 || gate->shape[0] != kHidden || gate->shape[1] != kIntermediate ||
            (gate->shape[2] != 256 && gate->shape[2] != 512))
            throw std::runtime_error("gate is not a supported IQ tensor [2560,640,256|512]");
        const int gu_type = gate->type;
        const uint64_t n_experts = gate->shape[2];
        if (static_cast<uint64_t>(expert) >= n_experts)
            throw std::invalid_argument("expert outside model expert count");
        const uint8_t* gate_data = model.shard(shard).tensor_data(*gate);
        const auto* up = model.find(prefix + "up_exps.weight", &shard);
        if (!up || up->type != static_cast<uint32_t>(gu_type) || up->shape != gate->shape)
            throw std::runtime_error("up codec/shape does not match gate");
        const uint8_t* up_data = model.shard(shard).tensor_data(*up);
        const auto* down = model.find(prefix + "down_exps.weight", &shard);
        if (!down || down->type != 20 || down->shape != std::vector<uint64_t>{kIntermediate, kHidden, n_experts})
            throw std::runtime_error("down is not IQ4_NL [640,2560,experts]");
        const uint8_t* down_data = model.shard(shard).tensor_data(*down);

        const auto layout = strata::kernels::native_expert_layout(gu_type, 20, kHidden, kIntermediate);
        std::vector<uint8_t> blob(layout.bytes);
        const auto* eg = gate_data + static_cast<size_t>(expert) * layout.up_off;
        const auto* eu = up_data + static_cast<size_t>(expert) * layout.up_off;
        const auto* ed = down_data + static_cast<size_t>(expert) * (layout.bytes - layout.down_off);
        std::memcpy(blob.data(), eg, layout.up_off);
        std::memcpy(blob.data() + layout.up_off, eu, layout.up_off);
        std::memcpy(blob.data() + layout.down_off, ed, layout.bytes - layout.down_off);
        auto input = read_f32(argv[4], kHidden);

        cudaStream_t stream = nullptr;
        uint8_t *d_blob = nullptr, *d_xq = nullptr;
        float *d_x = nullptr, *d_candidate = nullptr, *d_native = nullptr;
        void *d_candidate_scratch = nullptr, *d_native_scratch = nullptr;
        unsigned long long* d_ptr = nullptr;
        int32_t *d_starts = nullptr, *d_count = nullptr, *d_dst = nullptr, *d_tok = nullptr;
        check(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), "stream");
        const size_t q8_bytes = kHidden / 32 * 36;
        const size_t scratch_bytes = strata::kernels::native_expert_scratch_bytes(1, kIntermediate);
        const size_t candidate_scratch_bytes = strata::kernels::ninfer_iq2s_iq4nl_workspace_bytes(1, kIntermediate);
        if (candidate_scratch_bytes != scratch_bytes)
            throw std::runtime_error("NInfer and Strata grouped scratch layouts differ: " +
                                     std::to_string(candidate_scratch_bytes) + " vs " +
                                     std::to_string(scratch_bytes));
        check(cudaMalloc(&d_blob, blob.size()), "blob");
        check(cudaMalloc(&d_x, input.size() * sizeof(float)), "input");
        check(cudaMalloc(&d_xq, q8_bytes), "Q8_1 input");
        check(cudaMalloc(&d_candidate_scratch, scratch_bytes), "candidate workspace");
        check(cudaMalloc(&d_native_scratch, scratch_bytes), "Strata workspace");
        check(cudaMalloc(&d_candidate, kHidden * sizeof(float)), "candidate output");
        check(cudaMalloc(&d_native, kHidden * sizeof(float)), "Strata output");
        check(cudaMalloc(&d_ptr, sizeof(*d_ptr)), "group pointer");
        check(cudaMalloc(&d_starts, 2 * sizeof(int32_t)), "group starts");
        check(cudaMalloc(&d_count, sizeof(int32_t)), "group count");
        check(cudaMalloc(&d_dst, sizeof(int32_t)), "destination");
        check(cudaMalloc(&d_tok, sizeof(int32_t)), "token map");
        const unsigned long long blob_addr = reinterpret_cast<unsigned long long>(d_blob);
        const int32_t starts[]{0, 1}, count = 1, row = 0, token = 0;
        check(cudaMemcpyAsync(d_blob, blob.data(), blob.size(), cudaMemcpyHostToDevice, stream), "upload blob");
        check(cudaMemcpyAsync(d_x, input.data(), input.size() * sizeof(float), cudaMemcpyHostToDevice, stream), "upload input");
        check(cudaMemcpyAsync(d_ptr, &blob_addr, sizeof(blob_addr), cudaMemcpyHostToDevice, stream), "upload pointer");
        check(cudaMemcpyAsync(d_starts, starts, sizeof(starts), cudaMemcpyHostToDevice, stream), "upload starts");
        check(cudaMemcpyAsync(d_count, &count, sizeof(count), cudaMemcpyHostToDevice, stream), "upload count");
        check(cudaMemcpyAsync(d_dst, &row, sizeof(row), cudaMemcpyHostToDevice, stream), "upload destination");
        check(cudaMemcpyAsync(d_tok, &token, sizeof(token), cudaMemcpyHostToDevice, stream), "upload token");
        strata::kernels::native_quantize_q8_1(d_x, d_xq, kHidden, 1, stream);
        const std::vector<float> sentinel(kHidden, -12345.0f);
        check(cudaMemcpyAsync(d_candidate, sentinel.data(), sentinel.size() * sizeof(float), cudaMemcpyHostToDevice, stream), "init candidate");
        check(cudaMemcpyAsync(d_native, sentinel.data(), sentinel.size() * sizeof(float), cudaMemcpyHostToDevice, stream), "init native");

        if (gu_type == 22) {
            strata::kernels::ninfer_iq2s_iq4nl_backend_set(true);
            strata::kernels::ninfer_iq2s_iq4nl_expert_grouped(layout, d_ptr, d_starts, d_count, d_dst, d_tok,
                                                              1, 1, d_xq, d_candidate_scratch, d_candidate,
                                                              stream, 1);
        } else if (gu_type == 18) {
            strata::kernels::ninfer_iq3xxs_iq4nl_backend_set(true);
            strata::kernels::ninfer_iq3xxs_iq4nl_expert_grouped(layout, d_ptr, d_starts, d_count, d_dst, d_tok,
                                                               1, 1, d_xq, d_candidate_scratch, d_candidate,
                                                               stream, 1);
        } else {
            strata::kernels::ninfer_iq3s_iq4nl_backend_set(true);
            strata::kernels::ninfer_iq3s_iq4nl_expert_grouped(layout, d_ptr, d_starts, d_count, d_dst, d_tok,
                                                             1, 1, d_xq, d_candidate_scratch, d_candidate,
                                                             stream, 1);
        }
        strata::kernels::native_expert_grouped(layout, d_ptr, d_starts, d_count, d_dst, d_tok,
                                               1, 1, d_xq, d_native_scratch, d_native, stream, 1);
        std::vector<float> candidate(kHidden), native(kHidden);
        const size_t fa = (static_cast<size_t>(kIntermediate) * sizeof(float) + 255) & ~size_t(255);
        std::vector<float> candidate_gate(kIntermediate), candidate_up(kIntermediate);
        std::vector<float> native_gate(kIntermediate), native_up(kIntermediate);
        std::vector<uint8_t> candidate_hidden(kIntermediate / 32 * 36), native_hidden(kIntermediate / 32 * 36);
        check(cudaMemcpyAsync(candidate.data(), d_candidate, candidate.size() * sizeof(float), cudaMemcpyDeviceToHost, stream), "download candidate");
        check(cudaMemcpyAsync(native.data(), d_native, native.size() * sizeof(float), cudaMemcpyDeviceToHost, stream), "download Strata");
        auto* cs = static_cast<uint8_t*>(d_candidate_scratch);
        auto* ns = static_cast<uint8_t*>(d_native_scratch);
        check(cudaMemcpyAsync(candidate_gate.data(), cs, kIntermediate * sizeof(float), cudaMemcpyDeviceToHost, stream), "download candidate gate");
        check(cudaMemcpyAsync(candidate_up.data(), cs + fa, kIntermediate * sizeof(float), cudaMemcpyDeviceToHost, stream), "download candidate up");
        check(cudaMemcpyAsync(native_gate.data(), ns, kIntermediate * sizeof(float), cudaMemcpyDeviceToHost, stream), "download Strata gate");
        check(cudaMemcpyAsync(native_up.data(), ns + fa, kIntermediate * sizeof(float), cudaMemcpyDeviceToHost, stream), "download Strata up");
        check(cudaMemcpyAsync(candidate_hidden.data(), cs + 3 * fa, candidate_hidden.size(), cudaMemcpyDeviceToHost, stream), "download candidate hidden Q8_1");
        check(cudaMemcpyAsync(native_hidden.data(), ns + 3 * fa, native_hidden.size(), cudaMemcpyDeviceToHost, stream), "download Strata hidden Q8_1");
        check(cudaStreamSynchronize(stream), "synchronize");
        double err2 = 0.0, ref2 = 0.0, err1 = 0.0;
        float max_abs = 0.0f;
        size_t changed = 0, invalid = 0;
        for (int i = 0; i < kHidden; ++i) {
            const double d = static_cast<double>(candidate[i]) - native[i];
            err2 += d * d; ref2 += static_cast<double>(native[i]) * native[i];
            err1 += std::fabs(d); max_abs = std::max(max_abs, static_cast<float>(std::fabs(d)));
            changed += std::memcmp(&candidate[i], &native[i], sizeof(float)) != 0;
            invalid += !std::isfinite(candidate[i]) || candidate[i] == sentinel[i];
        }
        const double rel_l2 = std::sqrt(err2 / std::max(ref2, 1.0e-300));
        auto stage = [](const std::vector<float>& a, const std::vector<float>& b) {
            double e2 = 0.0, r2 = 0.0;
            float m = 0.0f;
            for (size_t i = 0; i < a.size(); ++i) {
                const double d = static_cast<double>(a[i]) - b[i];
                e2 += d * d; r2 += static_cast<double>(b[i]) * b[i];
                m = std::max(m, static_cast<float>(std::fabs(d)));
            }
            return std::pair<double, float>{std::sqrt(e2 / std::max(r2, 1.0e-300)), m};
        };
        const auto gate_error = stage(candidate_gate, native_gate);
        const auto up_error = stage(candidate_up, native_up);
        size_t hidden_bytes_differ = 0;
        for (size_t i = 0; i < candidate_hidden.size(); ++i) hidden_bytes_differ += candidate_hidden[i] != native_hidden[i];
        const uint64_t dispatch = gu_type == 22 ? strata::kernels::ninfer_iq2s_iq4nl_dispatch_count()
                                  : gu_type == 18 ? strata::kernels::ninfer_iq3xxs_iq4nl_dispatch_count()
                                                  : strata::kernels::ninfer_iq3s_iq4nl_dispatch_count();
        std::printf("NInfer %s/IQ4_NL grouped: layer=%d expert=%d bytes=%zu dispatch=%llu "
                    "relative_l2=%.9g relative_l1=%.9g max_abs=%.9g changed=%zu invalid=%zu\n",
                    gu_type == 22 ? "IQ2_S" : gu_type == 18 ? "IQ3_XXS" : "IQ3_S", layer, expert, blob.size(),
                    static_cast<unsigned long long>(dispatch),
                    rel_l2, err1 / std::max(std::sqrt(ref2 * kHidden), 1.0e-300), max_abs, changed, invalid);
        std::printf("stages: gate_rel_l2=%.9g gate_max_abs=%.9g up_rel_l2=%.9g up_max_abs=%.9g hidden_q8_bytes_differ=%zu/%zu\n",
                    gate_error.first, gate_error.second, up_error.first, up_error.second,
                    hidden_bytes_differ, candidate_hidden.size());
        if (dispatch != 1 || invalid != 0) return 1;
        cudaFree(d_tok); cudaFree(d_dst); cudaFree(d_count); cudaFree(d_starts); cudaFree(d_ptr);
        cudaFree(d_native); cudaFree(d_candidate); cudaFree(d_native_scratch); cudaFree(d_candidate_scratch);
        cudaFree(d_xq); cudaFree(d_x); cudaFree(d_blob); cudaStreamDestroy(stream);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "ninfer_iq_expert_parity: %s\n", e.what());
        return 1;
    }
}

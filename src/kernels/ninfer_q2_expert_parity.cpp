#include "strata/artifact/gguf_reader.hpp"
#include "strata/kernels/iq_kernels.hpp"
#include "strata/kernels/ninfer_q2_expert.hpp"
#include "strata/kernels/native_mmvq.hpp"

#include <cuda_runtime.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int kHidden = 2560;
constexpr int kIntermediate = 640;
constexpr double kMaxRelativeL2 = 5.0e-5;
constexpr double kMaxAbsolute = 1.0e-5;

void cuda_check(cudaError_t status, const char* operation) {
    if (status != cudaSuccess) throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
}

std::vector<uint8_t> read_bytes(const std::string& path, size_t expected) {
    std::ifstream input(path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open " + path);
    std::vector<uint8_t> bytes(expected);
    input.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    if (input.gcount() != static_cast<std::streamsize>(bytes.size()) || input.peek() != EOF)
        throw std::runtime_error(path + ": byte length does not match the declared vector");
    return bytes;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 7) {
        std::fprintf(stderr,
                     "usage: ninfer_q2_expert_parity shard-00001.gguf layer expert activation.f32 reference.f64 output.f32\n");
        return 2;
    }
    try {
        const std::string model_path = argv[1];
        const int layer = std::stoi(argv[2]);
        const int expert = std::stoi(argv[3]);
        const std::string activation_path = argv[4];
        const std::string reference_path = argv[5];
        const std::string output_path = argv[6];
        if (layer < 0 || expert < 0 || expert >= 512) throw std::invalid_argument("invalid layer/expert id");

        auto model = strata::GgufModel::open(model_path);
        const std::string prefix = "blk." + std::to_string(layer) + ".ffn_";
        size_t shard = 0;
        const auto* gate = model.find(prefix + "gate_exps.weight", &shard);
        if (!gate || gate->type != 42 || gate->shape != std::vector<uint64_t>{kHidden, kIntermediate, 512})
            throw std::runtime_error("gate tensor is not the expected Q2_0 [2560,640,512] tensor");
        const uint8_t* gate_data = model.shard(shard).tensor_data(*gate);
        const auto* up = model.find(prefix + "up_exps.weight", &shard);
        if (!up || up->type != 42 || up->shape != std::vector<uint64_t>{kHidden, kIntermediate, 512})
            throw std::runtime_error("up tensor is not the expected Q2_0 [2560,640,512] tensor");
        const uint8_t* up_data = model.shard(shard).tensor_data(*up);
        const auto* down = model.find(prefix + "down_exps.weight", &shard);
        if (!down || down->type != 42 || down->shape != std::vector<uint64_t>{kIntermediate, kHidden, 512})
            throw std::runtime_error("down tensor is not the expected Q2_0 [640,2560,512] tensor");
        const uint8_t* down_data = model.shard(shard).tensor_data(*down);

        constexpr size_t gu_row_bytes = kHidden / 64 * 18;
        constexpr size_t d_row_bytes = kIntermediate / 64 * 18;
        constexpr size_t one_expert_bytes = kIntermediate * gu_row_bytes;
        const void* expert_gate = gate_data + static_cast<size_t>(expert) * one_expert_bytes;
        const void* expert_up = up_data + static_cast<size_t>(expert) * one_expert_bytes;
        const void* expert_down = down_data + static_cast<size_t>(expert) * kHidden * d_row_bytes;

        const auto activation_bytes = read_bytes(activation_path, kHidden * sizeof(float));
        const auto reference_bytes = read_bytes(reference_path, kHidden * sizeof(double));
        std::vector<double> reference(kHidden);
        std::memcpy(reference.data(), reference_bytes.data(), reference_bytes.size());
        std::vector<float> output(kHidden, -12345.0f);
        float *device_x = nullptr, *device_workspace = nullptr, *device_output = nullptr;
        uint8_t *device_gate = nullptr, *device_up = nullptr, *device_down = nullptr;
        cudaStream_t stream = nullptr;
        cuda_check(cudaStreamCreateWithFlags(&stream, cudaStreamNonBlocking), "create stream");
        cuda_check(cudaMalloc(&device_gate, one_expert_bytes), "allocate gate");
        cuda_check(cudaMalloc(&device_up, one_expert_bytes), "allocate up");
        cuda_check(cudaMalloc(&device_down, kHidden * d_row_bytes), "allocate down");
        cuda_check(cudaMalloc(&device_x, kHidden * sizeof(float)), "allocate input");
        cuda_check(cudaMalloc(&device_workspace, strata::kernels::ninfer_q2_0_expert_workspace_bytes()),
                   "allocate workspace");
        cuda_check(cudaMalloc(&device_output, kHidden * sizeof(float)), "allocate output");
        cuda_check(cudaMemcpyAsync(device_gate, expert_gate, one_expert_bytes, cudaMemcpyHostToDevice, stream),
                   "copy gate");
        cuda_check(cudaMemcpyAsync(device_up, expert_up, one_expert_bytes, cudaMemcpyHostToDevice, stream), "copy up");
        cuda_check(cudaMemcpyAsync(device_down, expert_down, kHidden * d_row_bytes, cudaMemcpyHostToDevice, stream),
                   "copy down");
        cuda_check(cudaMemcpyAsync(device_x, activation_bytes.data(), activation_bytes.size(), cudaMemcpyHostToDevice,
                                   stream), "copy input");
        const std::vector<float> sentinel(kHidden, -12345.0f);
        cuda_check(cudaMemcpyAsync(device_output, sentinel.data(), kHidden * sizeof(float), cudaMemcpyHostToDevice,
                                   stream), "initialize output");
        strata::kernels::ninfer_q2_0_expert(device_gate, device_up, device_down, device_x, device_workspace,
                                            device_output, stream);
        cuda_check(cudaMemcpyAsync(output.data(), device_output, kHidden * sizeof(float), cudaMemcpyDeviceToHost,
                                   stream), "copy output");
        cuda_check(cudaStreamSynchronize(stream), "synchronize stream");

        double err2 = 0.0, ref2 = 0.0, max_abs = 0.0;
        size_t unwritten = 0;
        for (int i = 0; i < kHidden; ++i) {
            const double delta = static_cast<double>(output[i]) - reference[i];
            err2 += delta * delta;
            ref2 += reference[i] * reference[i];
            max_abs = std::max(max_abs, std::fabs(delta));
            unwritten += output[i] == -12345.0f || !std::isfinite(output[i]);
        }
        const double rel_l2 = std::sqrt(err2 / ref2);
        std::ofstream output_file(output_path, std::ios::binary);
        output_file.write(reinterpret_cast<const char*>(output.data()), output.size() * sizeof(float));
        if (!output_file) throw std::runtime_error("failed writing output vector");

        std::printf("NInfer-derived Q2_0 D3/D4: layer=%d expert=%d rel_l2=%.9g max_abs=%.9g unwritten=%zu "
                    "limits=(%.3g,%.3g) %s\n",
                    layer, expert, rel_l2, max_abs, unwritten, kMaxRelativeL2, kMaxAbsolute,
                    rel_l2 <= kMaxRelativeL2 && max_abs <= kMaxAbsolute && unwritten == 0 ? "PASS" : "FAIL");
        int failed = rel_l2 <= kMaxRelativeL2 && max_abs <= kMaxAbsolute && unwritten == 0 ? 0 : 1;

        // Exercise the grouped cache-slot ABI used by the service. The exact
        // expert bytes are packed in NativeExpertLayout order; one device group
        // and one routed entry keep this focused on the decode path; a
        // separate event-timed operator screen below is not end-to-end.
        const auto layout = strata::kernels::native_expert_layout(42, 42, kHidden, kIntermediate);
        std::vector<uint8_t> blob(layout.bytes);
        std::memcpy(blob.data(), expert_gate, layout.up_off);
        std::memcpy(blob.data() + layout.up_off, expert_up, layout.down_off - layout.up_off);
        std::memcpy(blob.data() + layout.down_off, expert_down, layout.bytes - layout.down_off);
        uint8_t *device_blob = nullptr, *device_xq = nullptr;
        uint8_t *candidate_scratch = nullptr, *native_scratch = nullptr;
        float *device_group_output = nullptr, *device_native_output = nullptr;
        unsigned long long* device_ptrs = nullptr;
        int32_t *device_starts = nullptr, *device_group_count = nullptr, *device_dst = nullptr, *device_tok = nullptr;
        const size_t q8_bytes = kHidden / 32 * 36;
        const size_t scratch_bytes = strata::kernels::native_expert_scratch_bytes(1, kIntermediate);
        cuda_check(cudaMalloc(&device_blob, blob.size()), "allocate grouped blob");
        cuda_check(cudaMalloc(&device_xq, q8_bytes), "allocate grouped Q8_1 input");
        cuda_check(cudaMalloc(&candidate_scratch, scratch_bytes), "allocate grouped NInfer workspace");
        cuda_check(cudaMalloc(&native_scratch, scratch_bytes), "allocate grouped Strata workspace");
        cuda_check(cudaMalloc(&device_group_output, kHidden * sizeof(float)), "allocate grouped NInfer output");
        cuda_check(cudaMalloc(&device_native_output, kHidden * sizeof(float)), "allocate grouped Strata output");
        cuda_check(cudaMalloc(&device_ptrs, sizeof(unsigned long long)), "allocate grouped pointers");
        cuda_check(cudaMalloc(&device_starts, 2 * sizeof(int32_t)), "allocate grouped starts");
        cuda_check(cudaMalloc(&device_group_count, sizeof(int32_t)), "allocate grouped count");
        cuda_check(cudaMalloc(&device_dst, sizeof(int32_t)), "allocate grouped destination map");
        cuda_check(cudaMalloc(&device_tok, sizeof(int32_t)), "allocate grouped token map");
        const unsigned long long blob_address = reinterpret_cast<unsigned long long>(device_blob);
        const int32_t starts[2] = {0, 1}, group_count = 1, row_map = 0, token_map = 0;
        cuda_check(cudaMemcpyAsync(device_blob, blob.data(), blob.size(), cudaMemcpyHostToDevice, stream),
                   "copy grouped blob");
        cuda_check(cudaMemcpyAsync(device_ptrs, &blob_address, sizeof(blob_address), cudaMemcpyHostToDevice, stream),
                   "copy grouped pointer");
        cuda_check(cudaMemcpyAsync(device_starts, starts, sizeof(starts), cudaMemcpyHostToDevice, stream),
                   "copy grouped starts");
        cuda_check(cudaMemcpyAsync(device_group_count, &group_count, sizeof(group_count), cudaMemcpyHostToDevice, stream),
                   "copy grouped count");
        cuda_check(cudaMemcpyAsync(device_dst, &row_map, sizeof(row_map), cudaMemcpyHostToDevice, stream),
                   "copy grouped destination map");
        cuda_check(cudaMemcpyAsync(device_tok, &token_map, sizeof(token_map), cudaMemcpyHostToDevice, stream),
                   "copy grouped token map");
        strata::kernels::native_quantize_q8_1(device_x, device_xq, kHidden, 1, stream);
        cuda_check(cudaMemcpyAsync(device_group_output, sentinel.data(), kHidden * sizeof(float), cudaMemcpyHostToDevice,
                                   stream), "initialize grouped NInfer output");
        cuda_check(cudaMemcpyAsync(device_native_output, sentinel.data(), kHidden * sizeof(float), cudaMemcpyHostToDevice,
                                   stream), "initialize grouped Strata output");
        const uint64_t calls_before = strata::kernels::ninfer_q2_0_expert_dispatch_count();
        strata::kernels::ninfer_q2_0_expert_grouped(layout, device_ptrs, device_starts, device_group_count,
                                                     device_dst, device_tok, 1, 1, device_xq,
                                                     candidate_scratch, device_group_output, stream, 1);
        strata::kernels::native_expert_grouped(layout, device_ptrs, device_starts, device_group_count,
                                               device_dst, device_tok, 1, 1, device_xq, native_scratch,
                                               device_native_output, stream, 1);
        std::vector<float> grouped_output(kHidden), native_output(kHidden);
        cuda_check(cudaMemcpyAsync(grouped_output.data(), device_group_output, kHidden * sizeof(float),
                                   cudaMemcpyDeviceToHost, stream), "copy grouped NInfer output");
        cuda_check(cudaMemcpyAsync(native_output.data(), device_native_output, kHidden * sizeof(float),
                                   cudaMemcpyDeviceToHost, stream), "copy grouped Strata output");
        cuda_check(cudaStreamSynchronize(stream), "synchronize grouped route");
        double route_err = 0.0, route_ref = 0.0;
        size_t route_unwritten = 0;
        for (int i = 0; i < kHidden; ++i) {
            const double delta = static_cast<double>(grouped_output[i]) - native_output[i];
            route_err += std::fabs(delta);
            route_ref += std::fabs(native_output[i]);
            route_unwritten += !std::isfinite(grouped_output[i]) || grouped_output[i] == -12345.0f;
        }
        const double route_rel_l1 = route_err / route_ref;
        const uint64_t calls = strata::kernels::ninfer_q2_0_expert_dispatch_count() - calls_before;
        std::printf("grouped resident route vs Strata Q2_0/Q8_1: rel_l1=%.9g unwritten=%zu NInfer_calls=%llu %s\n",
                    route_rel_l1, route_unwritten, static_cast<unsigned long long>(calls),
                    route_rel_l1 <= 2.0e-4 && route_unwritten == 0 && calls == 1 ? "PASS" : "FAIL");
        failed += route_rel_l1 <= 2.0e-4 && route_unwritten == 0 && calls == 1 ? 0 : 1;

        // Diagnostic device-timeline screen: seven interleaved paired blocks,
        // one resident expert and one token. This excludes model routing,
        // transfers and request overhead; it is not an end-to-end benchmark.
        auto run_candidate = [&] {
            strata::kernels::ninfer_q2_0_expert_grouped(layout, device_ptrs, device_starts, device_group_count,
                                                         device_dst, device_tok, 1, 1, device_xq,
                                                         candidate_scratch, device_group_output, stream, 1);
        };
        auto run_strata = [&] {
            strata::kernels::native_expert_grouped(layout, device_ptrs, device_starts, device_group_count,
                                                    device_dst, device_tok, 1, 1, device_xq, native_scratch,
                                                    device_native_output, stream, 1);
        };
        auto timed = [&](auto&& invoke, int iterations) {
            for (int i = 0; i < 12; ++i) invoke();
            cudaEvent_t begin = nullptr, end = nullptr;
            cuda_check(cudaEventCreate(&begin), "create benchmark start event");
            cuda_check(cudaEventCreate(&end), "create benchmark end event");
            cuda_check(cudaEventRecord(begin, stream), "record benchmark start");
            for (int i = 0; i < iterations; ++i) invoke();
            cuda_check(cudaEventRecord(end, stream), "record benchmark end");
            cuda_check(cudaEventSynchronize(end), "synchronize benchmark end");
            float elapsed_ms = 0.0f;
            cuda_check(cudaEventElapsedTime(&elapsed_ms, begin, end), "read benchmark events");
            cudaEventDestroy(end);
            cudaEventDestroy(begin);
            return static_cast<double>(elapsed_ms) * 1000.0 / iterations;
        };
        constexpr int kBenchIterations = 1000;
        std::vector<double> candidate_us, strata_us;
        for (int block = 0; block < 7; ++block) {
            if ((block & 1) == 0) {
                candidate_us.push_back(timed(run_candidate, kBenchIterations));
                strata_us.push_back(timed(run_strata, kBenchIterations));
            } else {
                strata_us.push_back(timed(run_strata, kBenchIterations));
                candidate_us.push_back(timed(run_candidate, kBenchIterations));
            }
        }
        auto median = [](std::vector<double> values) {
            std::sort(values.begin(), values.end());
            return values[values.size() / 2];
        };
        const auto candidate_range = std::minmax_element(candidate_us.begin(), candidate_us.end());
        const auto strata_range = std::minmax_element(strata_us.begin(), strata_us.end());
        std::printf("one-token resident operator device timeline (7 interleaved x %d): "
                    "Strata median=%.3f us range=[%.3f,%.3f], NInfer median=%.3f us range=[%.3f,%.3f], "
                    "ratio=%.3f\n",
                    kBenchIterations, median(strata_us), *strata_range.first, *strata_range.second,
                    median(candidate_us), *candidate_range.first, *candidate_range.second,
                    median(candidate_us) / median(strata_us));
        cudaFree(device_tok); cudaFree(device_dst); cudaFree(device_group_count); cudaFree(device_starts);
        cudaFree(device_ptrs); cudaFree(device_native_output); cudaFree(device_group_output);
        cudaFree(native_scratch); cudaFree(candidate_scratch); cudaFree(device_xq); cudaFree(device_blob);
        cudaFree(device_output); cudaFree(device_workspace); cudaFree(device_x);
        cudaFree(device_down); cudaFree(device_up); cudaFree(device_gate); cudaStreamDestroy(stream);
        return failed;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "ninfer_q2_expert_parity: %s\n", error.what());
        return 2;
    }
}

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
#include <utility>
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

        // Prefill-shaped grouped dispatch: three input tokens, three expert
        // groups and nine output entries. Nine entries exercise both the
        // 8-column quantizer limit and the bounded second chunk (8 + 1).
        constexpr int kMultiTokens = 3, kMultiGroups = 3, kMultiEntries = 9;
        std::vector<float> multi_x(kMultiTokens * kHidden);
        std::vector<float> activation(kHidden);
        std::memcpy(activation.data(), activation_bytes.data(), activation_bytes.size());
        std::copy(activation.begin(), activation.end(), multi_x.begin());
        for (int i = 0; i < kHidden; ++i) {
            multi_x[kHidden + i] = activation[i] * 0.75f;
            multi_x[2 * kHidden + i] = activation[i] * ((i & 1) ? -0.5f : 0.5f);
        }
        std::vector<uint8_t> multi_blob(kMultiGroups * layout.bytes);
        for (int group = 0; group < kMultiGroups; ++group) {
            const int id = expert + group;
            const void* g = gate_data + static_cast<size_t>(id) * one_expert_bytes;
            const void* u = up_data + static_cast<size_t>(id) * one_expert_bytes;
            const void* d = down_data + static_cast<size_t>(id) * kHidden * d_row_bytes;
            uint8_t* blob = multi_blob.data() + static_cast<size_t>(group) * layout.bytes;
            std::memcpy(blob, g, layout.up_off);
            std::memcpy(blob + layout.up_off, u, layout.down_off - layout.up_off);
            std::memcpy(blob + layout.down_off, d, layout.bytes - layout.down_off);
        }
        uint8_t *device_multi_blob = nullptr, *device_multi_xq = nullptr;
        uint8_t *candidate_multi_scratch = nullptr, *native_multi_scratch = nullptr;
        float *device_multi_output = nullptr, *device_multi_native_output = nullptr;
        unsigned long long* device_multi_ptrs = nullptr;
        int32_t *device_multi_starts = nullptr, *device_multi_count = nullptr;
        int32_t *device_multi_dst = nullptr, *device_multi_tok = nullptr;
        const size_t multi_x_bytes = multi_x.size() * sizeof(float);
        const size_t multi_q8_bytes = static_cast<size_t>(kMultiTokens) * kHidden / 32 * 36;
        const size_t multi_scratch_bytes = strata::kernels::native_expert_scratch_bytes(kMultiEntries, kIntermediate);
        cuda_check(cudaMalloc(&device_multi_blob, multi_blob.size()), "allocate multi-group blobs");
        cuda_check(cudaMalloc(&device_multi_xq, multi_q8_bytes), "allocate multi-token Q8_1 input");
        cuda_check(cudaMalloc(&candidate_multi_scratch, multi_scratch_bytes), "allocate multi-entry NInfer workspace");
        cuda_check(cudaMalloc(&native_multi_scratch, multi_scratch_bytes), "allocate multi-entry Strata workspace");
        cuda_check(cudaMalloc(&device_multi_output, kMultiEntries * kHidden * sizeof(float)), "allocate multi-entry NInfer output");
        cuda_check(cudaMalloc(&device_multi_native_output, kMultiEntries * kHidden * sizeof(float)), "allocate multi-entry Strata output");
        cuda_check(cudaMalloc(&device_multi_ptrs, kMultiGroups * sizeof(unsigned long long)), "allocate multi-group pointers");
        cuda_check(cudaMalloc(&device_multi_starts, (kMultiGroups + 1) * sizeof(int32_t)), "allocate multi-group starts");
        cuda_check(cudaMalloc(&device_multi_count, sizeof(int32_t)), "allocate multi-group count");
        cuda_check(cudaMalloc(&device_multi_dst, kMultiEntries * sizeof(int32_t)), "allocate multi-entry destinations");
        cuda_check(cudaMalloc(&device_multi_tok, kMultiEntries * sizeof(int32_t)), "allocate multi-entry token map");
        std::vector<unsigned long long> multi_ptrs(kMultiGroups);
        for (int group = 0; group < kMultiGroups; ++group)
            multi_ptrs[group] = reinterpret_cast<unsigned long long>(device_multi_blob + static_cast<size_t>(group) * layout.bytes);
        const int32_t multi_starts[kMultiGroups + 1] = {0, 4, 7, 9};
        const int32_t multi_dst[kMultiEntries] = {5, 0, 8, 1, 7, 2, 6, 3, 4};
        const int32_t multi_tok[kMultiEntries] = {0, 1, 2, 0, 1, 2, 1, 2, 0};
        const int32_t multi_group_count = kMultiGroups;
        cuda_check(cudaMemcpyAsync(device_multi_blob, multi_blob.data(), multi_blob.size(), cudaMemcpyHostToDevice, stream),
                   "copy multi-group blobs");
        cuda_check(cudaMemcpyAsync(device_multi_ptrs, multi_ptrs.data(), multi_ptrs.size() * sizeof(multi_ptrs[0]),
                                   cudaMemcpyHostToDevice, stream), "copy multi-group pointers");
        cuda_check(cudaMemcpyAsync(device_multi_starts, multi_starts, sizeof(multi_starts), cudaMemcpyHostToDevice, stream),
                   "copy multi-group starts");
        cuda_check(cudaMemcpyAsync(device_multi_count, &multi_group_count, sizeof(multi_group_count), cudaMemcpyHostToDevice,
                                   stream), "copy multi-group count");
        cuda_check(cudaMemcpyAsync(device_multi_dst, multi_dst, sizeof(multi_dst), cudaMemcpyHostToDevice, stream),
                   "copy multi-entry destinations");
        cuda_check(cudaMemcpyAsync(device_multi_tok, multi_tok, sizeof(multi_tok), cudaMemcpyHostToDevice, stream),
                   "copy multi-entry token map");
        float* device_multi_x = nullptr;
        cuda_check(cudaMalloc(&device_multi_x, multi_x_bytes), "allocate multi-token activations");
        cuda_check(cudaMemcpyAsync(device_multi_x, multi_x.data(), multi_x_bytes, cudaMemcpyHostToDevice, stream),
                   "copy multi-token activations");
        strata::kernels::native_quantize_q8_1(device_multi_x, device_multi_xq, kHidden, kMultiTokens, stream);
        const std::vector<float> multi_sentinel(kMultiEntries * kHidden, -12345.0f);
        cuda_check(cudaMemcpyAsync(device_multi_output, multi_sentinel.data(), multi_sentinel.size() * sizeof(float),
                                   cudaMemcpyHostToDevice, stream), "initialize multi-entry NInfer output");
        cuda_check(cudaMemcpyAsync(device_multi_native_output, multi_sentinel.data(), multi_sentinel.size() * sizeof(float),
                                   cudaMemcpyHostToDevice, stream), "initialize multi-entry Strata output");
        const uint64_t multi_calls_before = strata::kernels::ninfer_q2_0_expert_dispatch_count();
        strata::kernels::ninfer_q2_0_expert_grouped(layout, device_multi_ptrs, device_multi_starts, device_multi_count,
                                                     device_multi_dst, device_multi_tok, kMultiGroups, kMultiEntries,
                                                     device_multi_xq, candidate_multi_scratch, device_multi_output,
                                                     stream, kMultiGroups);
        strata::kernels::native_expert_grouped(layout, device_multi_ptrs, device_multi_starts, device_multi_count,
                                               device_multi_dst, device_multi_tok, kMultiGroups, kMultiEntries,
                                               device_multi_xq, native_multi_scratch, device_multi_native_output,
                                               stream, kMultiGroups);
        std::vector<float> multi_output(multi_sentinel.size()), multi_native_output(multi_sentinel.size());
        cuda_check(cudaMemcpyAsync(multi_output.data(), device_multi_output, multi_output.size() * sizeof(float),
                                   cudaMemcpyDeviceToHost, stream), "copy multi-entry NInfer output");
        cuda_check(cudaMemcpyAsync(multi_native_output.data(), device_multi_native_output,
                                   multi_native_output.size() * sizeof(float), cudaMemcpyDeviceToHost, stream),
                   "copy multi-entry Strata output");
        cuda_check(cudaStreamSynchronize(stream), "synchronize multi-entry grouped routes");
        double multi_err = 0.0, multi_ref = 0.0;
        size_t multi_unwritten = 0;
        for (size_t i = 0; i < multi_output.size(); ++i) {
            const double delta = static_cast<double>(multi_output[i]) - multi_native_output[i];
            multi_err += std::fabs(delta);
            multi_ref += std::fabs(multi_native_output[i]);
            multi_unwritten += !std::isfinite(multi_output[i]) || multi_output[i] == -12345.0f;
        }
        const double multi_rel_l1 = multi_err / multi_ref;
        const uint64_t multi_calls = strata::kernels::ninfer_q2_0_expert_dispatch_count() - multi_calls_before;
        const bool multi_pass = multi_rel_l1 <= 2.0e-4 && multi_unwritten == 0 && multi_calls == 1;
        std::printf("multi-token grouped Q2_0/Q8_1 prefill shape (tokens=%d entries=%d groups=%d): "
                    "rel_l1=%.9g unwritten=%zu NInfer_calls=%llu %s\n",
                    kMultiTokens, kMultiEntries, kMultiGroups, multi_rel_l1, multi_unwritten,
                    static_cast<unsigned long long>(multi_calls), multi_pass ? "PASS" : "FAIL");
        failed += multi_pass ? 0 : 1;

        // Exercise the current service prefill chunk boundaries with a full
        // top-10 route for each token. These synthetic activations preserve
        // real model weights and exact Strata Q8_1 quantization; this is an
        // operator functional/shape check, not a prompt-distribution test.
        auto check_prefill_shape = [&](int token_count) {
            constexpr int groups = 10;
            const int entries = token_count * groups;
            const size_t input_bytes = static_cast<size_t>(token_count) * kHidden * sizeof(float);
            const size_t input_q8_bytes = static_cast<size_t>(token_count) * (kHidden / 32) * 36;
            const size_t blob_bytes = static_cast<size_t>(groups) * layout.bytes;
            const size_t output_bytes = static_cast<size_t>(entries) * kHidden * sizeof(float);
            const size_t scratch = strata::kernels::native_expert_scratch_bytes(entries, kIntermediate);
            std::vector<float> inputs(static_cast<size_t>(token_count) * kHidden);
            for (int t = 0; t < token_count; ++t) {
                const float scale = (t & 1) ? -0.5f : 0.5f + static_cast<float>(t % 7) * 0.0625f;
                for (int i = 0; i < kHidden; ++i) inputs[static_cast<size_t>(t) * kHidden + i] = activation[i] * scale;
            }
            std::vector<uint8_t> blobs(blob_bytes);
            std::vector<unsigned long long> pointers(groups);
            std::vector<int32_t> starts(groups + 1), destinations(entries), tokens(entries);
            for (int g = 0; g < groups; ++g) {
                const int id = expert + g;
                const void* gptr = gate_data + static_cast<size_t>(id) * one_expert_bytes;
                const void* uptr = up_data + static_cast<size_t>(id) * one_expert_bytes;
                const void* dptr = down_data + static_cast<size_t>(id) * kHidden * d_row_bytes;
                uint8_t* blob = blobs.data() + static_cast<size_t>(g) * layout.bytes;
                std::memcpy(blob, gptr, layout.up_off);
                std::memcpy(blob + layout.up_off, uptr, layout.down_off - layout.up_off);
                std::memcpy(blob + layout.down_off, dptr, layout.bytes - layout.down_off);
                starts[g] = g * token_count;
                for (int t = 0; t < token_count; ++t) {
                    const int e = g * token_count + t;
                    destinations[e] = e;
                    tokens[e] = t;
                }
            }
            starts[groups] = entries;

            uint8_t *dev_blobs = nullptr, *dev_xq = nullptr, *candidate_ws = nullptr, *strata_ws = nullptr;
            float *dev_x = nullptr, *candidate_y = nullptr, *strata_y = nullptr;
            unsigned long long* dev_ptrs = nullptr;
            int32_t *dev_starts = nullptr, *dev_groups = nullptr, *dev_dst = nullptr, *dev_tok = nullptr;
            cuda_check(cudaMalloc(&dev_blobs, blob_bytes), "allocate boundary group weights");
            cuda_check(cudaMalloc(&dev_x, input_bytes), "allocate boundary activations");
            cuda_check(cudaMalloc(&dev_xq, input_q8_bytes), "allocate boundary Q8_1 activations");
            cuda_check(cudaMalloc(&candidate_ws, scratch), "allocate boundary NInfer workspace");
            cuda_check(cudaMalloc(&strata_ws, scratch), "allocate boundary Strata workspace");
            cuda_check(cudaMalloc(&candidate_y, output_bytes), "allocate boundary NInfer output");
            cuda_check(cudaMalloc(&strata_y, output_bytes), "allocate boundary Strata output");
            cuda_check(cudaMalloc(&dev_ptrs, groups * sizeof(unsigned long long)), "allocate boundary weight pointers");
            cuda_check(cudaMalloc(&dev_starts, (groups + 1) * sizeof(int32_t)), "allocate boundary group starts");
            cuda_check(cudaMalloc(&dev_groups, sizeof(int32_t)), "allocate boundary group count");
            cuda_check(cudaMalloc(&dev_dst, entries * sizeof(int32_t)), "allocate boundary output map");
            cuda_check(cudaMalloc(&dev_tok, entries * sizeof(int32_t)), "allocate boundary token map");
            for (int g = 0; g < groups; ++g)
                pointers[g] = reinterpret_cast<unsigned long long>(dev_blobs + static_cast<size_t>(g) * layout.bytes);
            cuda_check(cudaMemcpyAsync(dev_blobs, blobs.data(), blob_bytes, cudaMemcpyHostToDevice, stream),
                       "copy boundary group weights");
            cuda_check(cudaMemcpyAsync(dev_x, inputs.data(), input_bytes, cudaMemcpyHostToDevice, stream),
                       "copy boundary activations");
            cuda_check(cudaMemcpyAsync(dev_ptrs, pointers.data(), pointers.size() * sizeof(pointers[0]),
                                       cudaMemcpyHostToDevice, stream), "copy boundary weight pointers");
            cuda_check(cudaMemcpyAsync(dev_starts, starts.data(), starts.size() * sizeof(starts[0]),
                                       cudaMemcpyHostToDevice, stream), "copy boundary group starts");
            cuda_check(cudaMemcpyAsync(dev_groups, &groups, sizeof(groups), cudaMemcpyHostToDevice, stream),
                       "copy boundary group count");
            cuda_check(cudaMemcpyAsync(dev_dst, destinations.data(), destinations.size() * sizeof(destinations[0]),
                                       cudaMemcpyHostToDevice, stream), "copy boundary output map");
            cuda_check(cudaMemcpyAsync(dev_tok, tokens.data(), tokens.size() * sizeof(tokens[0]),
                                       cudaMemcpyHostToDevice, stream), "copy boundary token map");
            for (int first = 0; first < token_count; first += 8) {
                const int count = std::min(8, token_count - first);
                strata::kernels::native_quantize_q8_1(
                    dev_x + static_cast<size_t>(first) * kHidden,
                    dev_xq + static_cast<size_t>(first) * (kHidden / 32) * 36,
                    kHidden, count, stream);
            }
            std::vector<float> sentinels(static_cast<size_t>(entries) * kHidden, -12345.0f);
            cuda_check(cudaMemcpyAsync(candidate_y, sentinels.data(), output_bytes, cudaMemcpyHostToDevice, stream),
                       "initialize boundary NInfer output");
            cuda_check(cudaMemcpyAsync(strata_y, sentinels.data(), output_bytes, cudaMemcpyHostToDevice, stream),
                       "initialize boundary Strata output");
            const uint64_t calls_before = strata::kernels::ninfer_q2_0_expert_dispatch_count();
            strata::kernels::ninfer_q2_0_expert_grouped(layout, dev_ptrs, dev_starts, dev_groups, dev_dst, dev_tok,
                                                         groups, entries, dev_xq, candidate_ws, candidate_y,
                                                         stream, groups);
            strata::kernels::native_expert_grouped(layout, dev_ptrs, dev_starts, dev_groups, dev_dst, dev_tok,
                                                    groups, entries, dev_xq, strata_ws, strata_y, stream, groups);
            std::vector<float> candidate_out(sentinels.size()), strata_out(sentinels.size());
            cuda_check(cudaMemcpyAsync(candidate_out.data(), candidate_y, output_bytes, cudaMemcpyDeviceToHost, stream),
                       "read boundary NInfer output");
            cuda_check(cudaMemcpyAsync(strata_out.data(), strata_y, output_bytes, cudaMemcpyDeviceToHost, stream),
                       "read boundary Strata output");
            cuda_check(cudaStreamSynchronize(stream), "synchronize boundary grouped routes");
            double error = 0.0, reference_norm = 0.0;
            size_t unwritten = 0;
            for (size_t i = 0; i < candidate_out.size(); ++i) {
                error += std::fabs(static_cast<double>(candidate_out[i]) - strata_out[i]);
                reference_norm += std::fabs(static_cast<double>(strata_out[i]));
                unwritten += !std::isfinite(candidate_out[i]) || candidate_out[i] == -12345.0f;
            }
            const double rel_l1 = error / reference_norm;
            const uint64_t calls = strata::kernels::ninfer_q2_0_expert_dispatch_count() - calls_before;
            const bool pass = rel_l1 <= 2.0e-4 && unwritten == 0 && calls == 1;
            std::printf("full top-10 grouped Q2_0/Q8_1 prefill boundary (tokens=%d entries=%d groups=%d): "
                        "rel_l1=%.9g unwritten=%zu NInfer_calls=%llu %s\n",
                        token_count, entries, groups, rel_l1, unwritten, static_cast<unsigned long long>(calls),
                        pass ? "PASS" : "FAIL");
            // Operator-only throughput screen: inputs, routes, weights, output
            // buffers and workspaces are prepared before timing. Each arm sees
            // the same captured activation family and 10-expert grouped shape.
            constexpr int warmup_iterations = 5;
            constexpr int measured_iterations = 50;
            constexpr int paired_blocks = 7;
            auto invoke = [&](bool use_ninfer) {
                if (use_ninfer)
                    strata::kernels::ninfer_q2_0_expert_grouped(layout, dev_ptrs, dev_starts, dev_groups,
                        dev_dst, dev_tok, groups, entries, dev_xq, candidate_ws, candidate_y, stream, groups);
                else
                    strata::kernels::native_expert_grouped(layout, dev_ptrs, dev_starts, dev_groups,
                        dev_dst, dev_tok, groups, entries, dev_xq, strata_ws, strata_y, stream, groups);
            };
            cudaEvent_t event_start = nullptr, event_stop = nullptr;
            cuda_check(cudaEventCreate(&event_start), "create grouped timing start event");
            cuda_check(cudaEventCreate(&event_stop), "create grouped timing stop event");
            auto measure_us = [&](bool use_ninfer) {
                for (int i = 0; i < warmup_iterations; ++i) invoke(use_ninfer);
                cuda_check(cudaStreamSynchronize(stream), "synchronize grouped timing warmup");
                cuda_check(cudaEventRecord(event_start, stream), "record grouped timing start");
                for (int i = 0; i < measured_iterations; ++i) invoke(use_ninfer);
                cuda_check(cudaEventRecord(event_stop, stream), "record grouped timing stop");
                cuda_check(cudaEventSynchronize(event_stop), "synchronize grouped timing stop");
                float elapsed_ms = 0.0f;
                cuda_check(cudaEventElapsedTime(&elapsed_ms, event_start, event_stop), "read grouped timing");
                return static_cast<double>(elapsed_ms) * 1000.0 / measured_iterations;
            };
            std::vector<double> strata_us, ninfer_us, ratios;
            for (int block = 0; block < paired_blocks; ++block) {
                double s = 0.0, n = 0.0;
                if ((block & 1) == 0) { s = measure_us(false); n = measure_us(true); }
                else { n = measure_us(true); s = measure_us(false); }
                strata_us.push_back(s); ninfer_us.push_back(n); ratios.push_back(n / s);
            }
            auto median = [](std::vector<double> values) {
                std::sort(values.begin(), values.end());
                return values[values.size() / 2];
            };
            const double strata_median = median(strata_us);
            const double ninfer_median = median(ninfer_us);
            const double ratio_median = median(ratios);
            const auto bounds = [](const std::vector<double>& values) {
                const auto mm = std::minmax_element(values.begin(), values.end());
                return std::pair<double, double>{*mm.first, *mm.second};
            };
            const auto s_bounds = bounds(strata_us), n_bounds = bounds(ninfer_us);
            std::printf("grouped operator screen (tokens=%d entries=%d blocks=%d iterations/block=%d): "
                        "Strata median=%.3f us range=[%.3f,%.3f], NInfer median=%.3f us "
                        "range=[%.3f,%.3f], NInfer/Strata=%.3fx\n",
                        token_count, entries, paired_blocks, measured_iterations,
                        strata_median, s_bounds.first, s_bounds.second,
                        ninfer_median, n_bounds.first, n_bounds.second, ratio_median);
            cuda_check(cudaEventDestroy(event_stop), "destroy grouped timing stop event");
            cuda_check(cudaEventDestroy(event_start), "destroy grouped timing start event");
            cudaFree(dev_tok); cudaFree(dev_dst); cudaFree(dev_groups); cudaFree(dev_starts); cudaFree(dev_ptrs);
            cudaFree(strata_y); cudaFree(candidate_y); cudaFree(strata_ws); cudaFree(candidate_ws);
            cudaFree(dev_xq); cudaFree(dev_x); cudaFree(dev_blobs);
            return pass;
        };
        for (const int tokens : {64, 128}) failed += check_prefill_shape(tokens) ? 0 : 1;
        cudaFree(device_tok); cudaFree(device_dst); cudaFree(device_group_count); cudaFree(device_starts);
        cudaFree(device_ptrs); cudaFree(device_native_output); cudaFree(device_group_output);
        cudaFree(native_scratch); cudaFree(candidate_scratch); cudaFree(device_xq); cudaFree(device_blob);
        cudaFree(device_multi_x); cudaFree(device_multi_tok); cudaFree(device_multi_dst); cudaFree(device_multi_count);
        cudaFree(device_multi_starts); cudaFree(device_multi_ptrs); cudaFree(device_multi_native_output);
        cudaFree(device_multi_output); cudaFree(native_multi_scratch); cudaFree(candidate_multi_scratch);
        cudaFree(device_multi_xq); cudaFree(device_multi_blob);
        cudaFree(device_output); cudaFree(device_workspace); cudaFree(device_x);
        cudaFree(device_down); cudaFree(device_up); cudaFree(device_gate); cudaStreamDestroy(stream);
        return failed;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "ninfer_q2_expert_parity: %s\n", error.what());
        return 2;
    }
}

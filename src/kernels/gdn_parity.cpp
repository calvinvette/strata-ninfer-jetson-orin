// src/kernels/gdn_parity.cpp - P2.S2's test for the GDN recurrence, the conv and the two norms.
//
// `ref/gdn.py` carries eleven PROPERTY checks, several of which exist because a rival reading of the SOURCE
// produces well-formed output.  The four that the kernels here can be wrong about are re-pinned below, each
// asserted OBSERVABLE against a deliberately-wrong computation before the kernel is judged:
//
//   1. MODULO head pairing, h % h_k, not INTERLEAVE.  With H_k=2 and H_v=4 the two give [0,1,0,1] and
//      [0,0,1,1]: they differ at h=1 and h=2.  Both produce a full-rank state of the right shape.
//   2. Decay applied BEFORE the rank-1 update.  Applying it after is a one-line move that keeps every shape
//      and every magnitude.
//   3. The conv's SLIDE DIRECTION.  `kernel[0]` must read the OLDEST state row and the new input must land in
//      the LAST state row; reversing either is invisible on a symmetric state, so the state rows here are
//      labelled so each position is identifiable.
//   4. `l2_norm`'s `+ eps` is an absolute floor on the SQUARED NORM, not on the mean.  The mean reading
//      differs by sqrt(S) = 11.3x at S = 128.  `ref/gdn.py` PROPERTY 1 instruments the derivation, so it is
//      not taken on trust there either.
//
// It also checks the STATE LAYOUT, which is the one place these kernels intentionally differ from the
// reference: (S, h_v, S) with j fastest instead of (S, S, h_v).  A layout mix-up is silent, so the state is
// filled with a value that encodes its own coordinates.
#include "strata/kernels/gdn.hpp"
#include "strata/kernels/fused_gdn.hpp"
#include "strata/kernels/verify_kernels.hpp"

#include <cuda_runtime.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <map>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void check(cudaError_t e, const char* what) {
    if (e != cudaSuccess) {
        std::fprintf(stderr, "%s: %s\n", what, cudaGetErrorString(e));
        std::exit(1);
    }
}

float sigmoid_f(float x) { return 1.0f / (1.0f + std::exp(-x)); }

/// The reference's `gdn_step`, with switches for the rival readings.
///
/// `state` is passed in the REFERENCE layout (S, S, h_v) - i.e. (i, j, h) - so that this function is a
/// transcription of `ref/gdn.py` and not of the kernel.
void ref_step(std::vector<double>& state, const std::vector<float>& q, const std::vector<float>& k,
              const std::vector<float>& v, const std::vector<float>& gate, const std::vector<float>& beta,
              int S, int h_k, int h_v, std::vector<float>& o, bool modulo_heads, bool decay_first) {
    auto at = [&](int i, int j, int h) -> double& { return state[(size_t) (i * S + j) * h_v + h]; };
    std::vector<float> oo((size_t) h_v * S, 0.0f);
    for (int h = 0; h < h_v; ++h) {
        const int src = modulo_heads ? (h % h_k) : (h / (h_v / h_k));
        const double dec = std::exp((double) gate[(size_t) h]);
        const double b = (double) beta[(size_t) h];
        for (int j = 0; j < S; ++j) {
            if (decay_first) for (int i = 0; i < S; ++i) at(i, j, h) *= dec;
            double sk = 0;
            for (int i = 0; i < S; ++i) sk += at(i, j, h) * (double) k[(size_t) (src * S + i)];
            const double d = ((double) v[(size_t) (h * S + j)] - sk) * b;
            for (int i = 0; i < S; ++i) at(i, j, h) += (double) k[(size_t) (src * S + i)] * d;
            if (!decay_first) for (int i = 0; i < S; ++i) at(i, j, h) *= dec;
            double dot = 0;
            for (int i = 0; i < S; ++i) dot += at(i, j, h) * (double) q[(size_t) (src * S + i)];
            oo[(size_t) (h * S + j)] = (float) dot;
        }
    }
    o = oo;
}

/// `ref/gdn.py::conv_step` in its own (d_conv, C) row-major orientation.
void ref_conv(std::vector<float>& cs, const std::vector<float>& x, const std::vector<float>& kern, int C,
              int dc, std::vector<float>& out) {
    out.assign((size_t) C, 0.0f);
    for (int c = 0; c < C; ++c) {
        double acc = 0;
        for (int i = 0; i < dc - 1; ++i) acc += (double) cs[(size_t) (i * C + c)] * (double) kern[(size_t) (i * C + c)];
        acc += (double) x[(size_t) c] * (double) kern[(size_t) ((dc - 1) * C + c)];
        out[(size_t) c] = (float) acc;
        for (int i = 0; i < dc - 2; ++i) cs[(size_t) (i * C + c)] = cs[(size_t) ((i + 1) * C + c)];
        cs[(size_t) ((dc - 2) * C + c)] = x[(size_t) c];
    }
}

double rel_l1(const std::vector<float>& a, const std::vector<float>& b) {
    double d = 0, m = 0;
    for (size_t i = 0; i < a.size(); ++i) {
        d += std::fabs((double) a[i] - (double) b[i]);
        m += std::fabs((double) a[i]);
    }
    return d / (m > 1e-30 ? m : 1e-30);
}

#pragma pack(push, 1)
struct CommitHeader {
    char magic[8]; uint32_t version; int32_t layer; int64_t position;
    uint64_t recurrent_floats, state_floats; int32_t token, slot;
};
struct DiagHeader {
    char magic[8]; uint32_t version; int32_t layer, rows; int64_t pos0;
    uint64_t n_embd, conv_channels, v_heads, value_dim, state_floats; int32_t tokens[8];
};
#pragma pack(pop)
static_assert(sizeof(CommitHeader) == 48, "STGCMT1 header changed");
static_assert(sizeof(DiagHeader) == 100, "STGDIAG4 header changed");

struct ReplayInput { int32_t token = 0; std::vector<float> h, gate, beta, z; };

std::vector<char> read_binary(const char* path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error(std::string("cannot open ") + path);
    return std::vector<char>(std::istreambuf_iterator<char>(f), {});
}

std::map<int64_t, std::vector<float>> read_commit_capture(const char* path, int layer,
                                                         int64_t start_position, int64_t end_position) {
    const auto bytes = read_binary(path);
    std::map<int64_t, std::vector<float>> records;
    size_t offset = 0;
    while (offset < bytes.size()) {
        if (bytes.size() - offset < sizeof(CommitHeader)) throw std::runtime_error("truncated STGCMT1 header");
        CommitHeader h{}; std::memcpy(&h, bytes.data() + offset, sizeof(h));
        if (std::memcmp(h.magic, "STGCMT1", 7) || h.version != 1 || h.layer != layer)
            throw std::runtime_error("unexpected STGCMT1 record");
        const size_t data = offset + sizeof(h), nbytes = (size_t) h.state_floats * sizeof(float);
        if (data + nbytes > bytes.size()) throw std::runtime_error("truncated STGCMT1 payload");
        if (h.position == start_position || h.position == end_position) {
            std::vector<float> state((size_t) h.state_floats);
            std::memcpy(state.data(), bytes.data() + data, nbytes);
            records.emplace(h.position, std::move(state));
        }
        offset = data + nbytes;
    }
    if (!records.count(start_position) || !records.count(end_position))
        throw std::runtime_error("commit capture is missing the requested start/end positions");
    return records;
}

std::map<int64_t, ReplayInput> read_gdn_capture(const char* path, int layer,
                                               uint64_t& channels, uint64_t& heads, uint64_t& value_dim,
                                               int64_t position_a, int64_t position_b) {
    const auto bytes = read_binary(path);
    std::map<int64_t, ReplayInput> records;
    size_t offset = 0;
    while (offset < bytes.size()) {
        if (bytes.size() - offset < sizeof(DiagHeader)) throw std::runtime_error("truncated STGDIAG4 header");
        DiagHeader h{}; std::memcpy(&h, bytes.data() + offset, sizeof(h));
        if (std::memcmp(h.magic, "STGDIAG4", 8) || h.version != 4 || h.layer != layer || h.rows < 1 || h.rows > 8)
            throw std::runtime_error("unexpected STGDIAG4 record");
        if (channels && (channels != h.conv_channels || heads != h.v_heads || value_dim != h.value_dim))
            throw std::runtime_error("GDN capture geometry changed");
        channels = h.conv_channels; heads = h.v_heads; value_dim = h.value_dim;
        const uint64_t dims[] = {h.n_embd, h.conv_channels, h.conv_channels, h.v_heads, h.v_heads,
                                 h.value_dim, h.value_dim, h.n_embd, h.n_embd, h.n_embd};
        std::vector<std::vector<float>> fields(10);
        size_t cursor = offset + sizeof(h);
        for (size_t field = 0; field < 10; ++field) {
            const size_t count = (size_t) h.rows * (size_t) dims[field];
            const size_t nbytes = count * sizeof(float);
            if (cursor + nbytes > bytes.size()) throw std::runtime_error("truncated STGDIAG4 payload");
            fields[field].resize(count);
            std::memcpy(fields[field].data(), bytes.data() + cursor, nbytes);
            cursor += nbytes;
        }
        for (int row = 0; row < h.rows; ++row) {
            const int64_t pos = h.pos0 + row;
            if (pos != position_a && pos != position_b) continue;
            auto slice = [&](size_t field) {
                const size_t width = (size_t) dims[field];
                return std::vector<float>(fields[field].begin() + (size_t) row * width,
                                          fields[field].begin() + ((size_t) row + 1) * width);
            };
            ReplayInput x; x.token = h.tokens[row];
            x.h = slice(2); x.gate = slice(3); x.beta = slice(4); x.z = slice(5);
            records.emplace(pos, std::move(x));
        }
        offset = cursor;
    }
    if (!records.count(position_a) || !records.count(position_b))
        throw std::runtime_error("GDN capture is missing the requested positions");
    return records;
}

struct StateMetrics { size_t different; double rel, max_abs; };
StateMetrics state_metrics(const std::vector<float>& a, const std::vector<float>& b, size_t n) {
    size_t different = 0; double d2 = 0, b2 = 0, max_abs = 0;
    for (size_t i = 0; i < n; ++i) {
        const double d = (double) b[i] - a[i];
        different += a[i] != b[i]; d2 += d * d; b2 += (double) b[i] * b[i];
        max_abs = std::max(max_abs, std::fabs(d));
    }
    return {different, b2 ? std::sqrt(d2 / b2) : std::sqrt(d2), max_abs};
}

std::pair<std::vector<float>, std::vector<float>> replay_gdn(
    const std::vector<float>& initial, const std::map<int64_t, ReplayInput>& inputs,
    uint64_t channels, uint64_t heads, uint64_t value_dim, int h_k,
    int64_t position_a, int64_t position_b) {
    std::vector<float> state = initial;
    float *d_state = nullptr, *d_h = nullptr, *d_gate = nullptr, *d_beta = nullptr, *d_z = nullptr;
    float *d_gamma = nullptr, *d_y = nullptr;
    int32_t* d_keep = nullptr;
    cudaStream_t stream{};
    check(cudaStreamCreate(&stream), "create replay stream");
    auto allocate = [&](void** p, size_t bytes, const char* name) { check(cudaMalloc(p, bytes), name); };
    allocate((void**) &d_state, state.size() * sizeof(float), "allocate replay state");
    allocate((void**) &d_h, channels * sizeof(float), "allocate replay h");
    allocate((void**) &d_gate, heads * sizeof(float), "allocate replay gate");
    allocate((void**) &d_beta, heads * sizeof(float), "allocate replay beta");
    allocate((void**) &d_z, value_dim * sizeof(float), "allocate replay z");
    allocate((void**) &d_gamma, (value_dim / heads) * sizeof(float), "allocate replay gamma");
    allocate((void**) &d_y, value_dim * sizeof(float), "allocate replay y");
    allocate((void**) &d_keep, sizeof(int32_t), "allocate replay keep");
    const int32_t keep = 1;
    std::vector<float> after_2043, after_2044;
    std::vector<float> gamma((size_t) (value_dim / heads), 0.0f);
    check(cudaMemcpy(d_keep, &keep, sizeof(keep), cudaMemcpyHostToDevice), "copy replay keep");
    check(cudaMemcpy(d_gamma, gamma.data(), gamma.size() * sizeof(float), cudaMemcpyHostToDevice), "copy replay gamma");
    check(cudaMemcpy(d_state, state.data(), state.size() * sizeof(float), cudaMemcpyHostToDevice), "copy replay state");
    for (int64_t position : {position_a, position_b}) {
        const ReplayInput& x = inputs.at(position);
        check(cudaMemcpy(d_h, x.h.data(), x.h.size() * sizeof(float), cudaMemcpyHostToDevice), "copy replay h");
        check(cudaMemcpy(d_gate, x.gate.data(), x.gate.size() * sizeof(float), cudaMemcpyHostToDevice), "copy replay gate");
        check(cudaMemcpy(d_beta, x.beta.data(), x.beta.size() * sizeof(float), cudaMemcpyHostToDevice), "copy replay beta");
        check(cudaMemcpy(d_z, x.z.data(), x.z.size() * sizeof(float), cudaMemcpyHostToDevice), "copy replay z");
        strata::kernels::gdn_step_norm_multi(d_state, d_h, (int) channels, d_gate, d_beta, d_z, d_gamma,
                                             1e-6f, d_y, h_k, (int) heads, 1, d_keep, stream, 0, nullptr);
        check(cudaStreamSynchronize(stream), "synchronize GDN replay token");
        std::vector<float>& snapshot = position == position_a ? after_2043 : after_2044;
        snapshot.resize(state.size());
        check(cudaMemcpy(snapshot.data(), d_state, state.size() * sizeof(float), cudaMemcpyDeviceToHost),
              "read GDN replay token state");
    }
    check(cudaFree(d_state), "free replay state"); check(cudaFree(d_h), "free replay h");
    check(cudaFree(d_gate), "free replay gate"); check(cudaFree(d_beta), "free replay beta");
    check(cudaFree(d_z), "free replay z"); check(cudaFree(d_gamma), "free replay gamma");
    check(cudaFree(d_y), "free replay y"); check(cudaFree(d_keep), "free replay keep");
    check(cudaStreamDestroy(stream), "destroy replay stream");
    return {std::move(after_2043), std::move(after_2044)};
}

int replay_crossover(int64_t start_position, int64_t position_a, int64_t position_b,
                     const char* cpu_state_path, const char* staged_state_path,
                     const char* cpu_diag_path, const char* staged_diag_path) {
    constexpr int layer = 1, h_k = 16, h_v = 48, S = 128;
    constexpr size_t recurrent = (size_t) S * h_v * S;
    if (position_a != start_position + 1 || position_b != position_a + 1)
        throw std::runtime_error("replay positions must be consecutive after the start state");
    auto cpu_states = read_commit_capture(cpu_state_path, layer, start_position, position_b);
    auto staged_states = read_commit_capture(staged_state_path, layer, start_position, position_b);
    uint64_t channels = 0, heads = 0, value_dim = 0;
    auto cpu_inputs = read_gdn_capture(cpu_diag_path, layer, channels, heads, value_dim, position_a, position_b);
    auto staged_inputs = read_gdn_capture(staged_diag_path, layer, channels, heads, value_dim, position_a, position_b);
    if (heads != h_v || channels != 2 * S * h_k + value_dim || value_dim != (uint64_t) S * h_v)
        throw std::runtime_error("unexpected Flash-Next Q2_0 GDN geometry");
    for (int64_t p : {position_a, position_b})
        if (cpu_inputs.at(p).token != staged_inputs.at(p).token) throw std::runtime_error("paired token IDs differ");
    auto prefix = [&](const std::vector<float>& full) { return std::vector<float>(full.begin(), full.begin() + recurrent); };
    const auto cpu_start = prefix(cpu_states.at(start_position)), staged_start = prefix(staged_states.at(start_position));
    const auto cpu_actual = prefix(cpu_states.at(position_b)), staged_actual = prefix(staged_states.at(position_b));
    const auto cc = replay_gdn(cpu_start, cpu_inputs, channels, heads, value_dim, h_k, position_a, position_b);
    const auto cs = replay_gdn(cpu_start, staged_inputs, channels, heads, value_dim, h_k, position_a, position_b);
    const auto sc = replay_gdn(staged_start, cpu_inputs, channels, heads, value_dim, h_k, position_a, position_b);
    const auto ss = replay_gdn(staged_start, staged_inputs, channels, heads, value_dim, h_k, position_a, position_b);
    auto gate_only_inputs = cpu_inputs, beta_only_inputs = cpu_inputs;
    for (int64_t p : {position_a, position_b}) {
        gate_only_inputs.at(p).gate = staged_inputs.at(p).gate;
        beta_only_inputs.at(p).beta = staged_inputs.at(p).beta;
    }
    const auto gate_only = replay_gdn(cpu_start, gate_only_inputs, channels, heads, value_dim, h_k, position_a, position_b);
    const auto beta_only = replay_gdn(cpu_start, beta_only_inputs, channels, heads, value_dim, h_k, position_a, position_b);
    const auto m_cpu = state_metrics(cpu_actual, cc.second, recurrent);
    const auto m_staged = state_metrics(staged_actual, ss.second, recurrent);
    const bool route_matched_bitwise = m_cpu.different == 0 && m_cpu.max_abs == 0.0 &&
                                       m_staged.different == 0 && m_staged.max_abs == 0.0;
    const auto input_cpu_a = state_metrics(cc.first, cs.first, recurrent);
    const auto input_cpu_b = state_metrics(cc.second, cs.second, recurrent);
    const auto input_staged_a = state_metrics(sc.first, ss.first, recurrent);
    const auto input_staged_b = state_metrics(sc.second, ss.second, recurrent);
    const auto state_cpu_a = state_metrics(cc.first, sc.first, recurrent);
    const auto state_cpu_b = state_metrics(cc.second, sc.second, recurrent);
    const auto state_staged_a = state_metrics(cs.first, ss.first, recurrent);
    const auto state_staged_b = state_metrics(cs.second, ss.second, recurrent);
    const auto gate_only_a = state_metrics(cc.first, gate_only.first, recurrent);
    const auto gate_only_b = state_metrics(cc.second, gate_only.second, recurrent);
    const auto beta_only_a = state_metrics(cc.first, beta_only.first, recurrent);
    const auto beta_only_b = state_metrics(cc.second, beta_only.second, recurrent);
    auto print = [](const char* name, const StateMetrics& m, bool comma) {
        std::printf("    \"%s\": {\"different\": %zu, \"relative_l2\": %.9g, \"max_abs\": %.9g}%s\n",
                    name, m.different, m.rel, m.max_abs, comma ? "," : "");
    };
    std::printf("{\n  \"layer\": 1, \"start_position\": %lld, \"positions\": [%lld, %lld],\n",
                (long long) start_position, (long long) position_a, (long long) position_b);
    std::printf(
                "  \"geometry\": {\"state_size\": 128, \"key_heads\": 16, \"value_heads\": 48},\n"
                "  \"scope\": \"CUDA state recurrence only; gamma is zero and normalized output is not evaluated\",\n"
                "  \"route_matched_replays_bitwise\": %s,\n", route_matched_bitwise ? "true" : "false");
    print("replay_vs_captured_cpu", m_cpu, true); print("replay_vs_captured_staged", m_staged, true);
    auto emit_position = [&](const char* label, int64_t pos, const StateMetrics& input_cpu,
                             const StateMetrics& input_staged, const StateMetrics& state_cpu,
                             const StateMetrics& state_staged, const StateMetrics& gate,
                             const StateMetrics& beta, bool comma) {
        std::printf("  \"after_%s_%lld\": {\n", label, (long long) pos);
        print("input_effect_from_cpu_state", input_cpu, true);
        print("input_effect_from_staged_state", input_staged, true);
        print("initial_state_effect_with_cpu_input", state_cpu, true);
        print("initial_state_effect_with_staged_input", state_staged, true);
        print("gate_only_effect_from_cpu_state", gate, true);
        print("beta_only_effect_from_cpu_state", beta, false);
        std::printf("  }%s\n", comma ? "," : "");
    };
    emit_position("position", position_a, input_cpu_a, input_staged_a, state_cpu_a,
                  state_staged_a, gate_only_a, beta_only_a, true);
    emit_position("position", position_b, input_cpu_b, input_staged_b, state_cpu_b,
                  state_staged_b, gate_only_b, beta_only_b, false);
    std::printf("}\n");
    return route_matched_bitwise ? 0 : 2;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc == 6 && std::string(argv[1]) == "--replay-crossover") {
        try { return replay_crossover(2042, 2043, 2044, argv[2], argv[3], argv[4], argv[5]); }
        catch (const std::exception& e) { std::fprintf(stderr, "GDN replay: %s\n", e.what()); return 1; }
    }
    if (argc == 9 && std::string(argv[1]) == "--replay-crossover-window") {
        try {
            const int64_t start = std::stoll(argv[2]), a = std::stoll(argv[3]), b = std::stoll(argv[4]);
            return replay_crossover(start, a, b, argv[5], argv[6], argv[7], argv[8]);
        } catch (const std::exception& e) { std::fprintf(stderr, "GDN replay: %s\n", e.what()); return 1; }
    }
    bool selftest = false;
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--selftest") selftest = true;
        else { std::fprintf(stderr, "usage: gdn_parity [--selftest]\n"
                                    "       gdn_parity --replay-crossover CPU_STATE STAGED_STATE CPU_DIAG STAGED_DIAG\n"
                                    "       gdn_parity --replay-crossover-window START POS1 POS2 CPU_STATE STAGED_STATE CPU_DIAG STAGED_DIAG\n"); return 2; }
    }

    const int S = 128, h_k = 16, h_v = 48;      // the artifact's real geometry
    std::mt19937 rng(2024);
    std::normal_distribution<float> gauss(0.0f, 1.0f);
    int bad = 0;

    // ================= 1. the recurrence =================
    {
        // The state encodes its own coordinates, so a layout mix-up cannot pass: reading (i,j,h) where the
        // buffer holds (i,h,j) gives a DIFFERENT number, not a wrong-but-plausible one.
        std::vector<double> st_ref((size_t) S * S * h_v);
        std::vector<float> st_dev((size_t) S * h_v * S);
        for (int i = 0; i < S; ++i)
            for (int j = 0; j < S; ++j)
                for (int h = 0; h < h_v; ++h) {
                    const float val = (float) (0.001 * (i + 2 * j + 3 * h) - 1.0);
                    st_ref[(size_t) (i * S + j) * h_v + h] = val;
                    st_dev[(size_t) (i * h_v + h) * S + j] = val;   // (S, h_v, S), j fastest
                }

        std::vector<float> q((size_t) h_k * S), k((size_t) h_k * S), v((size_t) h_v * S), gate((size_t) h_v),
            beta((size_t) h_v);
        for (auto& x : q) x = gauss(rng) * 0.1f;
        for (auto& x : k) x = gauss(rng) * 0.1f;
        for (auto& x : v) x = gauss(rng);
        for (auto& x : gate) x = -(2.0f + 4.0f * (float) (rng() % 100) / 100.0f);   // dec in (0.0025, 0.135]
        for (auto& x : beta) x = (float) (rng() % 100) / 100.0f;

        std::vector<float> want_o;
        std::vector<double> st_mod = st_ref;
        ref_step(st_mod, q, k, v, gate, beta, S, h_k, h_v, want_o, true, true);

        // the traps
        {
            std::vector<double> a = st_ref;
            std::vector<float> oo;
            ref_step(a, q, k, v, gate, beta, S, h_k, h_v, oo, false, true);
            const double rel = rel_l1(want_o, oo);
            std::printf("  %-42s %-4s (%.2f%% apart)\n", "modulo vs interleave head pairing",
                        rel > 0.05 ? "yes" : "*** NO ***", rel * 100);
            if (!(rel > 0.05)) ++bad;
        }
        {
            std::vector<double> a = st_ref;
            std::vector<float> oo;
            ref_step(a, q, k, v, gate, beta, S, h_k, h_v, oo, true, false);
            const double rel = rel_l1(want_o, oo);
            std::printf("  %-42s %-4s (%.2f%% apart)\n", "decay before vs after the update",
                        rel > 0.05 ? "yes" : "*** NO ***", rel * 100);
            // The two readings differ by exactly `k (x) (beta * v * (1 - dec))`, so the fixture is only able
            // to see the trap when `dec` is far from 1 and `beta` is far from 0.  The first version used
            // gate in [-0.99, 0] - dec in [0.37, 1] - and managed 3.25%, which is a threshold the wrong
            // reading nearly clears.  Deep decay is also the realistic regime: `ssm_a = -exp(A_log) < 0` and
            // softplus is positive, so gate is comfortably negative in the real model.
            if (!(rel > 0.05)) ++bad;
        }

        // the kernel
        float *d_st = nullptr, *d_q = nullptr, *d_k = nullptr, *d_v = nullptr, *d_g = nullptr, *d_b = nullptr,
              *d_o = nullptr;
        check(cudaMalloc(&d_st, st_dev.size() * 4), "st");
        check(cudaMalloc(&d_q, q.size() * 4), "q");
        check(cudaMalloc(&d_k, k.size() * 4), "k");
        check(cudaMalloc(&d_v, v.size() * 4), "v");
        check(cudaMalloc(&d_g, gate.size() * 4), "g");
        check(cudaMalloc(&d_b, beta.size() * 4), "b");
        check(cudaMalloc(&d_o, (size_t) h_v * S * 4), "o");
        check(cudaMemcpy(d_st, st_dev.data(), st_dev.size() * 4, cudaMemcpyHostToDevice), "cst");
        check(cudaMemcpy(d_q, q.data(), q.size() * 4, cudaMemcpyHostToDevice), "cq");
        check(cudaMemcpy(d_k, k.data(), k.size() * 4, cudaMemcpyHostToDevice), "ck");
        check(cudaMemcpy(d_v, v.data(), v.size() * 4, cudaMemcpyHostToDevice), "cv");
        check(cudaMemcpy(d_g, gate.data(), gate.size() * 4, cudaMemcpyHostToDevice), "cg");
        check(cudaMemcpy(d_b, beta.data(), beta.size() * 4, cudaMemcpyHostToDevice), "cb");

        strata::kernels::GdnShapes sh{S, h_k, h_v};
        strata::kernels::gdn_step(d_st, d_q, d_k, d_v, d_g, d_b, d_o, sh, nullptr);

        std::vector<float> got_o((size_t) h_v * S), got_st(st_dev.size());
        check(cudaMemcpy(got_o.data(), d_o, got_o.size() * 4, cudaMemcpyDeviceToHost), "cgo");
        check(cudaMemcpy(got_st.data(), d_st, got_st.size() * 4, cudaMemcpyDeviceToHost), "cgst");

        // o, and the STATE read back through the declared layout
        const double rel_o = rel_l1(want_o, got_o);
        double rel_st = 0, mag_st = 0;
        for (int i = 0; i < S; ++i)
            for (int j = 0; j < S; ++j)
                for (int h = 0; h < h_v; ++h) {
                    const size_t dev = (size_t) (i * h_v + h) * S + j;
                    const double w = st_mod[(size_t) (i * S + j) * h_v + h];
                    rel_st += std::fabs(w - (double) got_st[dev]);
                    mag_st += std::fabs(w);
                }
        rel_st /= (mag_st > 1e-30 ? mag_st : 1e-30);
        std::printf("\n  %-42s rel %.3e\n", "o vs reference", rel_o);
        std::printf("  %-42s rel %.3e\n", "state (read via (S,h_v,S)) vs reference", rel_st);
        // The kernel accumulates in f32 and the reference in f64, and the state is a RECURRENCE over 128
        // terms, so 1e-5 is the arithmetic's floor here and not a structural allowance.
        if (!(rel_o <= 1e-5)) { std::printf("    *** o over 1e-5 ***\n"); ++bad; }
        if (!(rel_st <= 1e-5)) { std::printf("    *** state over 1e-5 ***\n"); ++bad; }

        // a zero state stays zero, and a zero gate/beta leaves the state untouched (the reference's
        // PROPERTY 4 setup) - a cheap independent invariant that no layout can fake
        {
            std::vector<float> zero(st_dev.size(), 0.0f), zg((size_t) h_v, 0.0f), zb((size_t) h_v, 0.0f);
            check(cudaMemcpy(d_st, zero.data(), zero.size() * 4, cudaMemcpyHostToDevice), "z0");
            check(cudaMemcpy(d_g, zg.data(), zg.size() * 4, cudaMemcpyHostToDevice), "z1");
            check(cudaMemcpy(d_b, zb.data(), zb.size() * 4, cudaMemcpyHostToDevice), "z2");
            strata::kernels::gdn_step(d_st, d_q, d_k, d_v, d_g, d_b, d_o, sh, nullptr);
            std::vector<float> zz(zero.size());
            check(cudaMemcpy(zz.data(), d_st, zz.size() * 4, cudaMemcpyDeviceToHost), "z3");
            double nz = 0;
            for (float x : zz) nz += std::fabs(x);
            const bool ok = nz == 0.0;
            std::printf("  %-42s %s\n", "gate=beta=0 from a zero state is a no-op", ok ? "yes" : "*** NO ***");
            if (!ok) ++bad;
        }

        // ephemeral state: unchanged when the state is untouched but beta=1 — the delta rule writing k*d
        cudaFree(d_st); cudaFree(d_q); cudaFree(d_k); cudaFree(d_v); cudaFree(d_g); cudaFree(d_b); cudaFree(d_o);
    }

    // ================= 2. the conv =================
    {
        const int C = 24, dc = 4;      // small, so the host reference is a plain loop
        // TWO DIFFERENT LAYOUTS MEET HERE, and this is where the first version of this test failed at 0.136.
        // `ref/gdn.py` carries the conv state as (d_conv-1, C) ROW-MAJOR - (i, c) at i*C + c - because it is
        // numpy.  The kernel carries it as (C, d_conv-1) with c fastest - c*(dc-1) + i - because that is
        // ggml's `ne = {d_conv-1, C}` with ne0 fast, and it is a runtime buffer so either is legal.  The
        // mapping between them is written out below rather than assumed, in both directions.
        std::vector<float> cs_ref((size_t) (dc - 1) * C), x((size_t) C), kern((size_t) dc * C);
        for (int i = 0; i < dc - 1; ++i)
            for (int c = 0; c < C; ++c) cs_ref[(size_t) (i * C + c)] = (float) (10 * (i + 1) + c);  // labelled
        for (int c = 0; c < C; ++c) x[(size_t) c] = (float) (100 + c);
        for (size_t i = 0; i < kern.size(); ++i) kern[i] = gauss(rng);

        auto to_dev_layout = [&](const std::vector<float>& r) {
            std::vector<float> d(r.size());
            for (int i = 0; i < dc - 1; ++i)
                for (int c = 0; c < C; ++c) d[(size_t) (c * (dc - 1) + i)] = r[(size_t) (i * C + c)];
            return d;
        };
        auto to_ref_layout = [&](const std::vector<float>& d) {
            std::vector<float> r(d.size());
            for (int i = 0; i < dc - 1; ++i)
                for (int c = 0; c < C; ++c) r[(size_t) (i * C + c)] = d[(size_t) (c * (dc - 1) + i)];
            return r;
        };

        std::vector<float> cs = to_dev_layout(cs_ref);
        std::vector<float> want;
        std::vector<float> cs_want_ref = cs_ref;
        ref_conv(cs_want_ref, x, kern, C, dc, want);
        const std::vector<float> cs_want = to_dev_layout(cs_want_ref);

        // THE LAYOUT: the manifest's `ssm_conv1d.weight` has ne = [d_conv, C], so ne0 = d_conv is fast.
        // The kernel takes `kW[c*dc + i]`; the reference's `kern` is (dc, C) row-major.  The transcription
        // below is the ONLY place the two meet.
        std::vector<float> kW((size_t) C * dc);
        for (int c = 0; c < C; ++c)
            for (int i = 0; i < dc; ++i) kW[(size_t) (c * dc + i)] = kern[(size_t) (i * C + c)];
        // and the rival reading, which must differ or the fixture cannot see a transposed weight
        std::vector<float> kW_wrong((size_t) C * dc);
        for (size_t i = 0; i < kern.size(); ++i) kW_wrong[i] = kern[i];
        {
            // apply the WRONG layout by hand: tap i of channel c is kW[c*dc+i] read as kW[i*C+c]
            std::vector<float> cs2 = cs;
            std::vector<float> out_bad((size_t) C, 0.0f);
            for (int c = 0; c < C; ++c) {
                double a = 0;
                for (int i = 0; i < dc - 1; ++i) a += (double) cs2[(size_t) (i * C + c)] * (double) kW_wrong[(size_t) (c * dc + i)];
                a += (double) x[(size_t) c] * (double) kW_wrong[(size_t) (c * dc + dc - 1)];
                out_bad[(size_t) c] = (float) a;
            }
            const double rel = rel_l1(want, out_bad);
            std::printf("\n  %-42s %-4s (%.1f%% apart)\n", "conv weight layout is observable",
                        rel > 0.05 ? "yes" : "*** NO ***", rel * 100);
            if (!(rel > 0.05)) ++bad;
        }

        float *d_cs = nullptr, *d_x = nullptr, *d_w = nullptr, *d_o = nullptr;
        check(cudaMalloc(&d_cs, cs.size() * 4), "cs");
        check(cudaMalloc(&d_x, x.size() * 4), "cx");
        check(cudaMalloc(&d_w, kW.size() * 4), "cw");
        check(cudaMalloc(&d_o, (size_t) C * 4), "co");
        check(cudaMemcpy(d_cs, cs.data(), cs.size() * 4, cudaMemcpyHostToDevice), "ccs");
        check(cudaMemcpy(d_x, x.data(), x.size() * 4, cudaMemcpyHostToDevice), "ccx");
        check(cudaMemcpy(d_w, kW.data(), kW.size() * 4, cudaMemcpyHostToDevice), "ccw");
        strata::kernels::gdn_conv_step(d_cs, d_x, d_w, d_o, C, dc, nullptr);
        std::vector<float> got((size_t) C), got_cs(cs.size());
        check(cudaMemcpy(got.data(), d_o, got.size() * 4, cudaMemcpyDeviceToHost), "cgo");
        check(cudaMemcpy(got_cs.data(), d_cs, got_cs.size() * 4, cudaMemcpyDeviceToHost), "cgs");
        const double rel_out = rel_l1(want, got), rel_cs = rel_l1(cs_want, got_cs);
        std::printf("  %-42s rel %.3e\n", "conv out vs reference", rel_out);
        std::printf("  %-42s rel %.3e\n", "conv state slide (mapped) vs reference", rel_cs);
        if (!(rel_out <= 1e-6)) { std::printf("    *** conv out ***\n"); ++bad; }
        if (!(rel_cs <= 1e-6)) { std::printf("    *** conv state ***\n"); ++bad; }
        cudaFree(d_cs); cudaFree(d_x); cudaFree(d_w); cudaFree(d_o);
    }

    // ================= 2b. accepted-prefix convolution history =================
    // After a verifier has computed T qkv rows, only the first n_keep rows may advance the three-row conv history.
    // Check every retained prefix, including zero, against an independent host selection from [history | qkv].
    {
        const int C = 259;     // crosses the 256-channel CUDA block edge
        const int max_t = strata::kernels::kVerifyMaxT;
        std::vector<float> initial((size_t) C * 3), qkv((size_t) max_t * C);
        for (size_t i = 0; i < initial.size(); ++i) initial[i] = (float) (i + 1) * 0.03125f - 9.0f;
        for (size_t i = 0; i < qkv.size(); ++i) qkv[i] = (float) (i + 1) * -0.015625f + 3.0f;
        float *d_history = nullptr, *d_qkv = nullptr;
        int32_t* d_keep = nullptr;
        check(cudaMalloc(&d_history, initial.size() * sizeof(float)), "conv commit history");
        check(cudaMalloc(&d_qkv, qkv.size() * sizeof(float)), "conv commit qkv");
        check(cudaMalloc(&d_keep, sizeof(int32_t)), "conv commit keep");
        check(cudaMemcpy(d_qkv, qkv.data(), qkv.size() * sizeof(float), cudaMemcpyHostToDevice), "conv commit upload qkv");
        int cases = 0, conv_bad = 0;
        for (int T = 1; T <= max_t; ++T) {
            for (int keep = 0; keep <= T; ++keep) {
                std::vector<float> expected(initial.size()), got(initial.size());
                for (int c = 0; c < C; ++c) {
                    for (int j = 0; j < 3; ++j) {
                        const int src = keep + j;
                        expected[(size_t) c * 3 + j] = src < 3 ? initial[(size_t) c * 3 + src]
                                                                  : qkv[(size_t) (src - 3) * C + c];
                    }
                }
                const int32_t n_keep = keep;
                check(cudaMemcpy(d_history, initial.data(), initial.size() * sizeof(float), cudaMemcpyHostToDevice),
                      "conv commit reset history");
                check(cudaMemcpy(d_keep, &n_keep, sizeof(n_keep), cudaMemcpyHostToDevice), "conv commit upload keep");
                strata::kernels::gdn_conv_commit(d_history, d_qkv, C, d_keep, nullptr);
                check(cudaMemcpy(got.data(), d_history, got.size() * sizeof(float), cudaMemcpyDeviceToHost),
                      "conv commit download history");
                ++cases;
                if (std::memcmp(got.data(), expected.data(), got.size() * sizeof(float)) != 0) {
                    std::printf("    *** gdn_conv_commit T=%d keep=%d differs from host prefix selection ***\n", T, keep);
                    ++bad; ++conv_bad;
                }
            }
        }
        std::vector<float> qkv_after(qkv.size());
        check(cudaMemcpy(qkv_after.data(), d_qkv, qkv_after.size() * sizeof(float), cudaMemcpyDeviceToHost),
              "conv commit verify qkv");
        const bool input_ok = std::memcmp(qkv.data(), qkv_after.data(), qkv.size() * sizeof(float)) == 0;
        std::printf("  %-42s %s (%d prefixes; T=1..8, keep=0..T, C=259)\n", "gdn_conv_commit accepted prefixes",
                    conv_bad == 0 && input_ok ? "bitwise" : "*** FAIL ***", cases);
        if (!input_ok) { std::printf("    *** gdn_conv_commit modified its qkv input ***\n"); ++bad; }
        cudaFree(d_history); cudaFree(d_qkv); cudaFree(d_keep);
    }

    // ================= 2c. verifier conv+L2 window parity =================
    // The verifier's multi-token convolution must produce the same h[t] as the ordinary single-token path with
    // the history advanced through each preceding token. Exercise the model channel width, each supported window,
    // and nonzero t_begin calls used by split verifier groups.
    {
        const int C = 10240, qk_heads = 16, max_t = strata::kernels::kVerifyMaxT;
        const float eps = 1e-6f;
        std::vector<float> initial((size_t) C * 3), qkv((size_t) max_t * C), conv_w((size_t) C * 4);
        for (auto& x : initial) x = gauss(rng) * 0.25f;
        for (auto& x : qkv) x = gauss(rng) * 0.25f;
        for (auto& x : conv_w) x = gauss(rng) * 0.2f;
        float *d_multi_hist = nullptr, *d_single_hist = nullptr, *d_qkv = nullptr, *d_w = nullptr;
        float *d_multi = nullptr, *d_single = nullptr, *d_split = nullptr;
        check(cudaMalloc(&d_multi_hist, initial.size() * sizeof(float)), "verify conv multi history");
        check(cudaMalloc(&d_single_hist, initial.size() * sizeof(float)), "verify conv single history");
        check(cudaMalloc(&d_qkv, qkv.size() * sizeof(float)), "verify conv qkv");
        check(cudaMalloc(&d_w, conv_w.size() * sizeof(float)), "verify conv weights");
        check(cudaMalloc(&d_multi, qkv.size() * sizeof(float)), "verify conv multi output");
        check(cudaMalloc(&d_single, qkv.size() * sizeof(float)), "verify conv single output");
        check(cudaMalloc(&d_split, qkv.size() * sizeof(float)), "verify conv split output");
        check(cudaMemcpy(d_qkv, qkv.data(), qkv.size() * sizeof(float), cudaMemcpyHostToDevice), "verify conv upload qkv");
        check(cudaMemcpy(d_w, conv_w.data(), conv_w.size() * sizeof(float), cudaMemcpyHostToDevice), "verify conv upload weights");
        int failures = 0;
        for (int T = 1; T <= max_t; ++T) {
            check(cudaMemcpy(d_multi_hist, initial.data(), initial.size() * sizeof(float), cudaMemcpyHostToDevice),
                  "verify conv reset multi history");
            check(cudaMemcpy(d_single_hist, initial.data(), initial.size() * sizeof(float), cudaMemcpyHostToDevice),
                  "verify conv reset single history");
            strata::kernels::gdn_conv_l2_multi(d_multi_hist, d_qkv, d_w, d_multi, C, qk_heads, eps, T, nullptr);
            for (int t = 0; t < T; ++t) {
                strata::kernels::fused_gdn_conv_l2(d_single_hist, d_qkv + (size_t) t * C, d_w,
                                                   d_single + (size_t) t * C, C, qk_heads, eps, nullptr);
                strata::kernels::gdn_conv_l2_multi(d_multi_hist, d_qkv, d_w, d_split, C, qk_heads, eps, 1, nullptr,
                                                   t, false);
            }
            check(cudaDeviceSynchronize(), "verify conv window synchronize");
            std::vector<float> got_multi((size_t) T * C), got_single((size_t) T * C), got_split((size_t) T * C);
            check(cudaMemcpy(got_multi.data(), d_multi, got_multi.size() * sizeof(float), cudaMemcpyDeviceToHost),
                  "verify conv read multi output");
            check(cudaMemcpy(got_single.data(), d_single, got_single.size() * sizeof(float), cudaMemcpyDeviceToHost),
                  "verify conv read single output");
            check(cudaMemcpy(got_split.data(), d_split, got_split.size() * sizeof(float), cudaMemcpyDeviceToHost),
                  "verify conv read split output");
            const bool single_equal = std::memcmp(got_multi.data(), got_single.data(), got_multi.size() * sizeof(float)) == 0;
            const bool split_equal = std::memcmp(got_multi.data(), got_split.data(), got_multi.size() * sizeof(float)) == 0;
            std::printf("  verifier conv+L2 T=%d: single-token %s, split t_begin %s\n", T,
                        single_equal ? "bitwise" : "*** FAIL ***", split_equal ? "bitwise" : "*** FAIL ***");
            failures += !single_equal + !split_equal;
        }
        if (failures) bad += failures;
        cudaFree(d_multi_hist); cudaFree(d_single_hist); cudaFree(d_qkv); cudaFree(d_w);
        cudaFree(d_multi); cudaFree(d_single); cudaFree(d_split);
    }

    // ================= 3. l2_norm =================
    {
        const int rows = 16, cols = 128;
        std::vector<float> x((size_t) rows * cols), x_ref;
        for (auto& val : x) val = gauss(rng) * 3.0f;
        x_ref = x;
        const float eps = 1e-6f;
        for (int r = 0; r < rows; ++r) {
            double acc = 0;
            for (int i = 0; i < cols; ++i) acc += (double) x_ref[(size_t) (r * cols + i)] * (double) x_ref[(size_t) (r * cols + i)];
            const float inv = (float) (1.0 / std::sqrt(acc + (double) eps));
            for (int i = 0; i < cols; ++i) x_ref[(size_t) (r * cols + i)] *= inv;
        }
        // The rival reading puts THE SAME eps on the MEAN instead of on the squared norm, which at
        // ||x||^2 ~ 1152 and cols = 128 changes the divisor from sqrt(1152) to sqrt(9) - a factor of 11.3, so
        // the trap is large here.  It would be a much smaller correction on a near-zero row, where the floor
        // is the whole answer; that regime is not what this fixture exercises.
        std::vector<float> x_mean = x;
        for (int r = 0; r < rows; ++r) {
            double acc = 0;
            for (int i = 0; i < cols; ++i) acc += (double) x_mean[(size_t) (r * cols + i)] * (double) x_mean[(size_t) (r * cols + i)];
            const float inv = (float) (1.0 / std::sqrt(acc / cols + (double) eps));
            for (int i = 0; i < cols; ++i) x_mean[(size_t) (r * cols + i)] *= inv;
        }
        const double rel_trap = rel_l1(x_ref, x_mean);
        std::printf("\n  %-42s %-4s (%.1f%% apart)\n", "eps on sum vs on mean is observable",
                    rel_trap > 0.05 ? "yes" : "*** NO ***", rel_trap * 100);
        if (!(rel_trap > 0.05)) ++bad;

        float* d_x = nullptr;
        check(cudaMalloc(&d_x, x.size() * 4), "lx");
        check(cudaMemcpy(d_x, x.data(), x.size() * 4, cudaMemcpyHostToDevice), "lcx");
        strata::kernels::gdn_l2_norm(d_x, rows, cols, eps, nullptr);
        std::vector<float> got(x.size());
        check(cudaMemcpy(got.data(), d_x, got.size() * 4, cudaMemcpyDeviceToHost), "lcg");
        const double rel = rel_l1(x_ref, got);
        std::printf("  %-42s rel %.3e\n", "l2_norm vs reference", rel);
        if (!(rel <= 1e-6)) ++bad;
        cudaFree(d_x);
    }

    // ================= 4. the closing norm =================
    {
        const int S2 = 128, hv2 = 8;
        std::vector<float> o((size_t) hv2 * S2), z((size_t) hv2 * S2), sn((size_t) S2), y_ref((size_t) hv2 * S2);
        for (auto& val : o) val = gauss(rng);
        for (auto& val : z) val = gauss(rng);
        for (auto& val : sn) val = 1.0f + 0.1f * gauss(rng);
        const float eps = 1e-6f;
        for (int h = 0; h < hv2; ++h) {
            double acc = 0;
            for (int i = 0; i < S2; ++i) acc += (double) o[(size_t) (h * S2 + i)] * (double) o[(size_t) (h * S2 + i)];
            const float inv = (float) (1.0 / std::sqrt(acc / S2 + (double) eps));
            for (int i = 0; i < S2; ++i)
                y_ref[(size_t) (h * S2 + i)] = o[(size_t) (h * S2 + i)] * inv * sn[(size_t) i] *
                                              sigmoid_f(z[(size_t) (h * S2 + i)]);
        }
        float *d_o = nullptr, *d_z = nullptr, *d_sn = nullptr, *d_y = nullptr;
        check(cudaMalloc(&d_o, o.size() * 4), "no");
        check(cudaMalloc(&d_z, z.size() * 4), "nz");
        check(cudaMalloc(&d_sn, sn.size() * 4), "ns");
        check(cudaMalloc(&d_y, y_ref.size() * 4), "ny");
        check(cudaMemcpy(d_o, o.data(), o.size() * 4, cudaMemcpyHostToDevice), "nco");
        check(cudaMemcpy(d_z, z.data(), z.size() * 4, cudaMemcpyHostToDevice), "ncz");
        check(cudaMemcpy(d_sn, sn.data(), sn.size() * 4, cudaMemcpyHostToDevice), "ncs");
        strata::kernels::gdn_out_norm(d_o, d_z, d_sn, d_y, hv2, S2, eps, nullptr);
        std::vector<float> got(y_ref.size());
        check(cudaMemcpy(got.data(), d_y, got.size() * 4, cudaMemcpyDeviceToHost), "ncy");
        const double rel = rel_l1(y_ref, got);
        std::printf("\n  %-42s rel %.3e\n", "out norm (rms * ssm_norm * sigmoid z)", rel);
        if (!(rel <= 1e-6)) ++bad;

        // SiLU instead of sigmoid is the qwen3.5 reading; `ref/gdn.py` says this artifact does NOT use it
        std::vector<float> y_silu(y_ref.size());
        for (int h = 0; h < hv2; ++h) {
            double acc = 0;
            for (int i = 0; i < S2; ++i) acc += (double) o[(size_t) (h * S2 + i)] * (double) o[(size_t) (h * S2 + i)];
            const float inv = (float) (1.0 / std::sqrt(acc / S2 + (double) eps));
            for (int i = 0; i < S2; ++i) {
                const float zz = z[(size_t) (h * S2 + i)];
                y_silu[(size_t) (h * S2 + i)] =
                    o[(size_t) (h * S2 + i)] * inv * sn[(size_t) i] * (zz / (1.0f + std::exp(-zz)));
            }
        }
        const double rel_silu = rel_l1(y_ref, y_silu);
        std::printf("  %-42s %-4s (%.2f%% apart)\n", "sigmoid vs SiLU on the gate is observable",
                    rel_silu > 0.05 ? "yes" : "*** NO ***", rel_silu * 100);
        if (!(rel_silu > 0.05)) ++bad;
        cudaFree(d_o); cudaFree(d_z); cudaFree(d_sn); cudaFree(d_y);
    }

    // ================= 5. the verify-window kernels, T = 1..8, bitwise against the single-token kernels =================
    // gdn_ab_multi and gdn_step_norm_multi are documented as bitwise `fused_gdn_ab` / `fused_gdn_step_norm` per
    // token (verify_kernels.hpp). Every T from 1 to kVerifyMaxT is its own exact-T instantiation, so each is run,
    // and every output and the state are compared with memcmp (not a tolerance).
    {
        const int n_embd = 2560, qk = S * h_k, C = 2 * qk + S * h_v, vd = S * h_v;
        const float eps = 1e-6f;
        auto bf16_of = [](float f) {
            uint32_t u;
            std::memcpy(&u, &f, 4);
            return (uint16_t) (u >> 16);
        };
        std::vector<uint16_t> wa((size_t) h_v * n_embd), wb((size_t) h_v * n_embd);
        for (auto& w : wa) w = bf16_of(gauss(rng) * 0.05f);
        for (auto& w : wb) w = bf16_of(gauss(rng) * 0.05f);
        std::vector<float> dt((size_t) h_v), ssm_a((size_t) h_v), gamma((size_t) S);
        for (auto& x : dt) x = gauss(rng);
        for (auto& x : ssm_a) x = -(0.1f + (float) (rng() % 100) / 50.0f);
        for (auto& x : gamma) x = 1.0f + 0.1f * gauss(rng);
        std::vector<float> st0((size_t) S * h_v * S);
        for (auto& x : st0) x = gauss(rng) * 0.1f;

        auto dev = [&](size_t bytes) {
            void* p = nullptr;
            check(cudaMalloc(&p, bytes), "m5");
            return p;
        };
        auto up = [&](const void* h, size_t bytes) {
            void* p = dev(bytes);
            check(cudaMemcpy(p, h, bytes, cudaMemcpyHostToDevice), "u5");
            return p;
        };
        auto down = [&](std::vector<float>& h, const void* d) {
            check(cudaMemcpy(h.data(), d, h.size() * 4, cudaMemcpyDeviceToHost), "d5");
        };
        auto d_wa = (uint16_t*) up(wa.data(), wa.size() * 2);
        auto d_wb = (uint16_t*) up(wb.data(), wb.size() * 2);
        auto d_dt = (float*) up(dt.data(), dt.size() * 4);
        auto d_sa = (float*) up(ssm_a.data(), ssm_a.size() * 4);
        auto d_gm = (float*) up(gamma.data(), gamma.size() * 4);
        int ab_bad = 0, sn_bad = 0, ab_n = 0, sn_n = 0;
        for (int T = 1; T <= strata::kernels::kVerifyMaxT; ++T) {
            // --- alpha/beta
            std::vector<float> x((size_t) T * n_embd);
            for (auto& v : x) v = gauss(rng);
            auto d_x = (float*) up(x.data(), x.size() * 4);
            auto d_g = (float*) dev((size_t) T * h_v * 4), d_b = (float*) dev((size_t) T * h_v * 4);
            auto d_gr = (float*) dev((size_t) T * h_v * 4), d_br = (float*) dev((size_t) T * h_v * 4);
            strata::kernels::gdn_ab_multi(d_x, d_wa, d_wb, d_dt, d_sa, d_g, d_b, n_embd, h_v, T, nullptr);
            for (int t = 0; t < T; ++t)
                strata::kernels::fused_gdn_ab(d_x + (size_t) t * n_embd, d_wa, d_wb, d_dt, d_sa, d_gr + (size_t) t * h_v,
                                              d_br + (size_t) t * h_v, n_embd, h_v, nullptr);
            std::vector<float> g((size_t) T * h_v), b(g.size()), gr(g.size()), br(g.size());
            down(g, d_g); down(b, d_b); down(gr, d_gr); down(br, d_br);
            ++ab_n;
            if (std::memcmp(g.data(), gr.data(), g.size() * 4) != 0 || std::memcmp(b.data(), br.data(), b.size() * 4) != 0) {
                std::printf("    *** gdn_ab_multi T=%d differs from fused_gdn_ab (memcmp) ***\n", T);
                ++ab_bad;
            }
            cudaFree(d_x); cudaFree(d_g); cudaFree(d_b); cudaFree(d_gr); cudaFree(d_br);

            // --- the recurrence + output norm
            std::vector<float> h((size_t) T * C), gate((size_t) T * h_v), beta((size_t) T * h_v), z((size_t) T * vd);
            for (auto& v : h) v = gauss(rng) * 0.1f;
            for (auto& v : gate) v = -(0.5f + 3.0f * (float) (rng() % 100) / 100.0f);
            for (auto& v : beta) v = (float) (rng() % 100) / 100.0f;
            for (auto& v : z) v = gauss(rng);
            auto d_h = (float*) up(h.data(), h.size() * 4);
            auto d_gate = (float*) up(gate.data(), gate.size() * 4);
            auto d_beta = (float*) up(beta.data(), beta.size() * 4);
            auto d_z = (float*) up(z.data(), z.size() * 4);
            auto d_y = (float*) dev((size_t) T * vd * 4);
            auto d_yr = (float*) dev((size_t) T * vd * 4);
            auto d_st = (float*) dev(st0.size() * 4);
            auto d_sr = (float*) dev(st0.size() * 4);
            int32_t* d_nk = (int32_t*) dev(4);
            // the reference chain (the single-token kernel), n tokens, into d_sr / d_yr
            auto run_ref = [&](int n) {
                check(cudaMemcpy(d_sr, st0.data(), st0.size() * 4, cudaMemcpyHostToDevice), "r0");
                for (int t = 0; t < n; ++t)
                    strata::kernels::fused_gdn_step_norm(d_sr, d_h + (size_t) t * C, d_h + (size_t) t * C + qk,
                                                         d_h + (size_t) t * C + 2 * qk, d_gate + (size_t) t * h_v,
                                                         d_beta + (size_t) t * h_v, d_z + (size_t) t * vd, d_gm, eps,
                                                         d_yr + (size_t) t * vd, h_k, h_v, nullptr);
            };
            std::vector<float> y((size_t) T * vd), yr(y.size()), st(st0.size()), sr(st0.size());
            // (name, n_keep tokens or -1 = verify half, t_out_begin)
            struct Case { const char* name; int n_keep; int tb; };
            std::vector<Case> cases = {{"verify", -1, 0}, {"verify tb", -1, T > 1 ? T / 2 : 0}, {"commit", T, 0},
                                       {"commit tb", T, T / 2}, {"commit state only", T, T}};
            // A verifier accepts a prefix, not just all tokens or the last token. Check every legal retained length,
            // including zero, against a fresh single-token replay from identical state. This exercises the kernel's
            // state result directly; API publication and KV/conv/PLE state still need the model-level transaction test.
            for (int keep = 0; keep <= T; ++keep) cases.push_back({"commit prefix", keep, 0});
            for (const Case& c : cases) {
                check(cudaMemcpy(d_st, st0.data(), st0.size() * 4, cudaMemcpyHostToDevice), "s0");
                check(cudaMemset(d_y, 0, (size_t) T * vd * 4), "y0");
                check(cudaMemset(d_yr, 0, (size_t) T * vd * 4), "yr0");
                const int n = c.n_keep < 0 ? T : c.n_keep;
                if (c.n_keep >= 0) check(cudaMemcpy(d_nk, &c.n_keep, 4, cudaMemcpyHostToDevice), "nk");
                strata::kernels::gdn_step_norm_multi(d_st, d_h, C, d_gate, d_beta, d_z, d_gm, eps, d_y, h_k, h_v, T,
                                                     c.n_keep >= 0 ? d_nk : nullptr, nullptr, c.tb);
                run_ref(n);
                down(y, d_y); down(yr, d_yr); down(st, d_st); down(sr, d_sr);
                bool ok = true;
                size_t y_bad = 0, y_all = 0;
                for (int t = c.tb; t < n; ++t) {
                    for (int i = 0; i < vd; ++i, ++y_all)
                        if (std::memcmp(&y[(size_t) t * vd + i], &yr[(size_t) t * vd + i], 4) != 0) ++y_bad;
                }
                if (y_bad) ok = false;
                // the verify half leaves the state untouched; the commit half writes the state after n tokens
                const std::vector<float>& want_st = c.n_keep < 0 ? st0 : sr;
                if (std::memcmp(st.data(), want_st.data(), st.size() * 4) != 0) ok = false;
                ++sn_n;
                if (!ok) {
                    std::printf("    *** gdn_step_norm_multi T=%d '%s' differs from fused_gdn_step_norm (memcmp): %zu of %zu y words%s ***\n",
                                T, c.name, y_bad, y_all,
                                std::memcmp(st.data(), (c.n_keep < 0 ? st0 : sr).data(), st.size() * 4) != 0 ? ", state too" : "");
                    ++sn_bad;
                }
            }
            cudaFree(d_h); cudaFree(d_gate); cudaFree(d_beta); cudaFree(d_z); cudaFree(d_y); cudaFree(d_yr); cudaFree(d_st);
            cudaFree(d_sr); cudaFree(d_nk);
        }
        cudaFree(d_wa); cudaFree(d_wb); cudaFree(d_dt); cudaFree(d_sa); cudaFree(d_gm);
        std::printf("\n  %-42s %s (%d cases)\n", "gdn_ab_multi T=1..8 == fused_gdn_ab", ab_bad ? "*** NO ***" : "bitwise", ab_n);
        std::printf("  %-42s %s (%d cases)\n", "gdn_step_norm_multi T=1..8 == single-token", sn_bad ? "*** NO ***" : "bitwise", sn_n);
        bad += ab_bad + sn_bad;
    }

    std::printf("\ngdn: %d failures\n", bad);
    if (bad) return 1;
    if (selftest) std::printf("gdn_parity OK\n");
    return 0;
}

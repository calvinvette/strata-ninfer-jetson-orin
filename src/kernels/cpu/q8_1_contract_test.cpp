// Independent scalar contract oracle for the production Q8_1 scalar/NEON routes.
#include "strata/kernels/cpu/expert.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <vector>

namespace c = strata::kernels::cpu;

static void oracle(const float* x, int n, c::ActQ& out) {
    out.nchunks = n / c::QKA;
    for (int b = 0; b < out.nchunks; ++b) {
        const float* p = x + b * c::QKA;
        float amax = 0.f;
        for (int i = 0; i < c::QKA; ++i) amax = std::fmax(amax, std::fabs(p[i]));
        const float scale = amax > 0.f ? amax / 127.f : 0.f;
        const float inv = scale > 0.f ? 1.f / scale : 0.f;
        int32_t sum = 0;
        for (int i = 0; i < c::QKA; ++i) {
            const float scaled = p[i] * inv;
            int32_t q = static_cast<int32_t>(scaled + (scaled >= 0.f ? 0.5f : -0.5f));
            q = q < -127 ? -127 : (q > 127 ? 127 : q);
            out.q[b * c::QKA + i] = static_cast<int8_t>(q);
            sum += q;
        }
        out.scale[b] = scale;
        out.sum[b] = sum;
        out.hx[b] = scale * static_cast<float>(sum);
    }
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const char* env = std::getenv("STRATA_Q8_1_NEON");
    const bool expect_neon = std::strcmp(argv[1], "neon") == 0;
    if (expect_neon != (env != nullptr && std::strcmp(env, "1") == 0)) {
        std::fprintf(stderr, "test invocation does not match STRATA_Q8_1_NEON mode\n");
        return 2;
    }
    std::mt19937 rng(0x81a11u);
    std::vector<float> x(c::H);
    c::ActQ actual{}, expected{};
    int failures = 0;
    for (const int n : {c::H, c::FF}) {
        x.resize(n);
        for (int trial = 0; trial < 96; ++trial) {
            for (int i = 0; i < n; ++i) {
                const int block = i / c::QKA;
                if (trial == 0) x[i] = 0.f;
                else if (trial == 1) {
                    static constexpr float ties[] = {-127.f, -63.5f, -1.5f, -0.5f, 0.f, 0.5f, 1.5f, 63.5f};
                    x[i] = ties[i % 8];
                } else if (trial == 2) x[i] = (i % c::QKA == c::QKA - 1) ? 127.f : float(i % 31 - 15) + 0.5f;
                else x[i] = float(int(rng() % 20001) - 10000) * std::ldexp(1.f / 317.f, block % 16 - 12);
            }
            oracle(x.data(), n, expected);
            c::act_quant_q8_1(x.data(), n, actual);
            for (int b = 0; b < n / c::QKA; ++b) {
                if (actual.scale[b] != expected.scale[b] || actual.sum[b] != expected.sum[b] ||
                    actual.hx[b] != expected.hx[b] ||
                    std::memcmp(actual.q + b * c::QKA, expected.q + b * c::QKA, c::QKA) != 0) ++failures;
            }
        }
    }
    std::printf("Q8_1 independent scalar oracle mode=%s widths=%d,%d trials=96 mismatched_blocks=%d\n",
                expect_neon ? "neon" : "scalar", c::H, c::FF, failures);
    return failures ? 1 : 0;
}

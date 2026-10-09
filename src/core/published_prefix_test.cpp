#include "strata/core/published_prefix.hpp"

#include <cstdio>

using strata::core::PublishedPrefix;
using strata::core::published_prefix;

namespace {
int failures = 0;
int checks = 0;

void check(PublishedPrefix got, int count, bool eos, const char* label) {
    ++checks;
    if (got.count != count || got.eos != eos) {
        ++failures;
        std::printf("FAIL %s: got (%d,%d), expected (%d,%d)\n", label, got.count, got.eos, count, eos);
    }
}
}

int main() {
    constexpr int64_t eos_ids[] = {248044, 248046};
    constexpr int32_t out[] = {11, 12, 13, 14, 15};
    constexpr int32_t with_eos[] = {11, 248046, 13, 14};

    // available is the matched prefix's outputs (accepted drafts plus anchor).
    check(published_prefix(out, 1, 0, 8, eos_ids, 2, true), 1, false, "zero accepted drafts");
    check(published_prefix(out, 0, 0, 8, eos_ids, 2, true), 0, false, "empty verifier output");
    check(published_prefix(out, 3, 0, 8, eos_ids, 2, true), 3, false, "intermediate accepted prefix");
    check(published_prefix(out, 5, 0, 8, eos_ids, 2, true), 5, false, "all accepted outputs");
    check(published_prefix(out, 5, 3, 5, eos_ids, 2, true), 2, false, "output-budget clipping");
    check(published_prefix(with_eos, 4, 0, 8, eos_ids, 2, true), 2, true, "EOS included and suffix rejected");
    check(published_prefix(with_eos, 4, 0, 8, eos_ids, 2, false), 4, false, "EOS ignored when stop disabled");
    check(published_prefix(out, 5, 5, 5, eos_ids, 2, true), 0, false, "already at output limit");
    check(published_prefix(out, 5, 0, 0, eos_ids, 2, true), 0, false, "zero output limit");
    check(published_prefix(out, 5, 0, 8, nullptr, 0, true), 5, false, "empty EOS list");
    check(published_prefix(nullptr, 5, 0, 8, eos_ids, 2, true), 0, false, "null output guard");

    std::printf("published_prefix: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}

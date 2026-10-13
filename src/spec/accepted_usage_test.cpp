#include "strata/spec/accepted_usage.hpp"

#include <cstdio>
#include <vector>

namespace {
int failures = 0;

void check(bool ok, const char* name) {
    if (!ok) {
        std::fprintf(stderr, "FAIL: %s\n", name);
        ++failures;
    }
}

std::vector<float> run(std::size_t committed, float rejected_suffix) {
    std::vector<float> usage{10.0f, 20.0f};
    std::vector<float> rows{
        1.0f, 2.0f, rejected_suffix, rejected_suffix + 1.0f,
        3.0f, 4.0f, rejected_suffix + 2.0f, rejected_suffix + 3.0f,
    };
    const bool ok = strata::spec::commit_accepted_usage(usage, rows, 4, committed);
    check(ok, "valid accepted-prefix commit");
    check(rows.empty(), "successful commit retires verifier staging");
    return usage;
}
}  // namespace

int main() {
    check(run(0, 1000.0f) == std::vector<float>({10.0f, 20.0f}), "zero commit adds no staged usage");
    check(run(1, 1000.0f) == std::vector<float>({11.0f, 23.0f}), "one-row commit adds only row zero");
    check(run(2, 1000.0f) == std::vector<float>({13.0f, 27.0f}), "intermediate commit adds accepted rows");
    check(run(4, 1000.0f) == std::vector<float>({2014.0f, 2032.0f}), "full commit includes every verifier row");
    check(run(2, 1000.0f) == run(2, -1000.0f), "rejected suffix mutation cannot change accepted usage");

    std::vector<float> usage{5.0f};
    std::vector<float> rows{7.0f, 999.0f, 999.0f, 999.0f};
    check(strata::spec::commit_accepted_usage(usage, rows, 4, 1) && usage[0] == 12.0f,
          "first verifier transaction commits");
    rows.assign({2.0f});
    check(strata::spec::commit_accepted_usage(usage, rows, 1, 1) && usage[0] == 14.0f,
          "next transaction accepts a different window size");

    usage = {3.0f};
    rows = {4.0f, 5.0f};
    check(!strata::spec::commit_accepted_usage(usage, rows, 2, 3) && usage[0] == 3.0f && rows.size() == 2,
          "over-commit rejects without mutation");
    rows = {4.0f};
    check(!strata::spec::commit_accepted_usage(usage, rows, 2, 1) && usage[0] == 3.0f && rows.size() == 1,
          "wrong staging size rejects without mutation");

    std::printf("accepted_usage_test: %s\n", failures ? "FAILED" : "OK");
    return failures ? 1 : 0;
}

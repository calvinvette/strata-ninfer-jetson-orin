#include "strata/spec/accepted_window.hpp"

#include <cstdio>
#include <limits>

namespace {
int failures = 0;
int checks = 0;

void check(bool ok, const char* message) {
    ++checks;
    if (!ok) {
        ++failures;
        std::fprintf(stderr, "FAIL: %s\n", message);
    }
}
}

int main() {
    using strata::spec::AcceptedWindow;
    using strata::spec::cap_accepted_window;

    // Every verifier window size and lookup-chain length is tested against each
    // possible next adaptation boundary. Accepted rows can never cross it.
    for (int mtp = 1; mtp <= 4; ++mtp) {
        for (int chained = 0; chained <= 4; ++chained) {
            for (int64_t allowance = 1; allowance <= 10; ++allowance) {
                AcceptedWindow window;
                check(cap_accepted_window(mtp, chained, allowance, window),
                      "valid accepted window is capped");
                const int expected = allowance < mtp + chained
                    ? static_cast<int>(allowance) : mtp + chained;
                check(window.total() == expected,
                      "capped window ends at the earlier of proposal or boundary");
                check(window.mtp >= 1 && window.chained >= 0,
                      "capped window retains its anchor and nonnegative chain");

                // If the verifier accepts fewer rows than the cap, it has not
                // crossed the boundary; full acceptance lands exactly on it.
                const int64_t before = 17;
                for (int accepted = 0; accepted <= window.total(); ++accepted) {
                    const int64_t committed = before + accepted;
                    check(committed <= before + allowance,
                          "accepted prefix cannot cross the next adaptation boundary");
                }
            }
        }
    }

    AcceptedWindow unchanged;
    check(cap_accepted_window(4, 3, std::numeric_limits<int64_t>::max(), unchanged) &&
              unchanged.mtp == 4 && unchanged.chained == 3,
          "large allowance leaves the proposed window unchanged");

    AcceptedWindow invalid{7, 9};
    check(!cap_accepted_window(0, 1, 1, invalid) && invalid.mtp == 7 && invalid.chained == 9,
          "zero MTP window is rejected without mutating the result");
    check(!cap_accepted_window(2, -1, 1, invalid) && invalid.mtp == 7 && invalid.chained == 9,
          "negative lookup chain is rejected without mutating the result");
    check(!cap_accepted_window(2, 1, 0, invalid) && invalid.mtp == 7 && invalid.chained == 9,
          "nonpositive boundary allowance is rejected without mutating the result");
    check(!cap_accepted_window(std::numeric_limits<int>::max(), 1, 1, invalid) &&
              invalid.mtp == 7 && invalid.chained == 9,
          "window-size overflow is rejected without mutating the result");

    std::printf("accepted_window_test: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}

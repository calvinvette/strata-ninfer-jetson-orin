#pragma once

#include <cstdint>
#include <limits>

namespace strata::spec {

struct AcceptedWindow {
    int mtp = 0;
    int chained = 0;

    int total() const { return mtp + chained; }
};

// Keep an accepted-only adaptive update boundary at the end of a verifier window.
// A capped window may shorten the MTP portion, the lookup-chain portion, or both,
// but it must always retain at least the verifier anchor row.
inline bool cap_accepted_window(int mtp, int chained, int64_t allowance,
                               AcceptedWindow& result) {
    if (mtp < 1 || chained < 0 || allowance < 1 ||
        chained > std::numeric_limits<int>::max() - mtp) {
        return false;
    }

    const int proposed = mtp + chained;
    const int total = allowance < proposed ? static_cast<int>(allowance) : proposed;
    if (total < mtp) {
        result = {total, 0};
    } else {
        result = {mtp, total - mtp};
    }
    return true;
}

}  // namespace strata::spec

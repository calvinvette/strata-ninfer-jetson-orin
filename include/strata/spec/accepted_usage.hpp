#pragma once

#include <cstddef>
#include <limits>
#include <vector>

namespace strata::spec {

// Commit only the verifier rows that became persistent tokens. Rows are stored
// expert-major: each expert owns one counter per verifier input row.
inline bool commit_accepted_usage(std::vector<float>& usage, std::vector<float>& usage_rows,
                                 std::size_t window_rows, std::size_t accepted_rows) {
    if (accepted_rows > window_rows ||
        (window_rows != 0 && usage.size() > std::numeric_limits<std::size_t>::max() / window_rows) ||
        usage_rows.size() != usage.size() * window_rows)
        return false;

    for (std::size_t expert = 0; expert < usage.size(); ++expert)
        for (std::size_t row = 0; row < accepted_rows; ++row)
            usage[expert] += usage_rows[expert * window_rows + row];

    // A verifier transaction is single-use. Clearing on a zero-length commit
    // also prevents canceled/rejected suffix rows from contaminating the next
    // request, whose window may have a different size.
    usage_rows.clear();
    return true;
}

}  // namespace strata::spec

#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>

namespace strata::core {

struct PublishedPrefix {
    int count = 0;
    bool eos = false;
};

// The verifier may accept more outputs than the caller can publish. Commit only
// the corresponding verifier inputs, stopping after the published EOS token.
inline PublishedPrefix published_prefix(const int32_t* outputs, int available,
                                         int64_t already_published, int64_t output_limit,
                                         const int64_t* eos_ids, std::size_t eos_count,
                                         bool stop_on_eos) {
    PublishedPrefix result;
    if (outputs == nullptr || available <= 0 || already_published >= output_limit) return result;
    for (int i = 0; i < available && already_published + result.count < output_limit && !result.eos; ++i) {
        ++result.count;
        result.eos = stop_on_eos && eos_ids != nullptr && eos_count > 0 &&
            std::find(eos_ids, eos_ids + eos_count, (int64_t) outputs[i]) != eos_ids + eos_count;
    }
    return result;
}

}  // namespace strata::core

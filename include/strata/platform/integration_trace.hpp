// Opt-in observations at existing owners; this is not an admission ledger.
// Requested payload bytes are not physical backing, driver memory or capacity.
#pragma once

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

namespace strata::platform::integration_trace {

inline bool enabled() {
    static const bool on = [] {
        const char* value = std::getenv("STRATA_INTEGRATION_TRACE");
        return value && value[0] == '1' && value[1] == '\0';
    }();
    return on;
}

// owner/kind are compile-time labels, never user input. A single stdio call
// keeps concurrent records together. Steady-clock time aligns with the harness.
inline void event(const char* owner, const char* kind, const void* instance,
                  const void* allocation, uint64_t bytes, int device, uint64_t count = 0) {
    if (!enabled()) return;
    const double now = std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    std::fprintf(stderr,
        "strata integration: {\"schema\":1,\"monotonic_s\":%.9f,\"owner\":\"%s\","
        "\"kind\":\"%s\",\"instance\":%llu,\"allocation\":%llu,\"requested_bytes\":%llu,"
        "\"device\":%d,\"count\":%llu}\n", now, owner, kind,
        (unsigned long long) reinterpret_cast<uintptr_t>(instance),
        (unsigned long long) reinterpret_cast<uintptr_t>(allocation),
        (unsigned long long) bytes, device, (unsigned long long) count);
}

// A planned budget hold is metadata, not an allocation or physical-memory
// observation. Keep it in a separate event kind so summaries never add it to
// observed backing bytes.
inline void reservation(const char* label, const void* instance, uint64_t bytes, int device) {
    if (!enabled() || bytes == 0) return;
    const double now = std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    std::fprintf(stderr,
        "strata integration: {\"schema\":1,\"monotonic_s\":%.9f,\"owner\":\"%s\","
        "\"kind\":\"reservation\",\"instance\":%llu,\"allocation\":0,\"requested_bytes\":%llu,"
        "\"device\":%d,\"count\":0}\n", now, label,
        (unsigned long long) reinterpret_cast<uintptr_t>(instance),
        (unsigned long long) bytes, device);
}

}  // namespace strata::platform::integration_trace

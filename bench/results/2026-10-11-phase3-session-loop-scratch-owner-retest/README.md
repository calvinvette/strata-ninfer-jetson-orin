# SessionLoopScratch mapped-host owner trace — Orin — 2026-10-11

A focused CUDA lifecycle test exercised `SessionLoopScratch::init()` and
`free()` with a 65,536-byte mapped, pinned host buffer. `cudaHostGetDevicePointer`
confirmed the mapping. The opt-in trace recorded exactly one
`session-loop-scratch-host` allocation and one matching free; a second `free()`
was idempotent and emitted no extra event. The event reported device `-1` because
the owner is host-backed.

The test passed under the ordinary six-GiB supervisor with minimum host
`MemAvailable` of 26,399,694,848 bytes (24.59 GiB). This directly tests the
scratch owner's allocation lifecycle, not the full legacy session-loop graph
route; the validated native pack does not exercise that route. The separate
`session-replay-prefix-scratch` events are source-instrumented but not runtime
covered here. Full verbose CTest output and supervisor telemetry are retained in
`supervisor/`. The parsed owner ledger in `trace-summary.json` reports 1/1 events, a 65,536-byte peak and zero live requested bytes. A separate [trace-disabled run](../2026-10-11-phase3-session-loop-scratch-trace-off/README.md) emitted no owner events. CUDA and maestro1 HIP build identities are recorded in
`backend-builds.json`; maestro1 provides compile evidence only.

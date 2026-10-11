# Phase 3 owner/PLE regression after session scratch instrumentation — Orin — 2026-10-11

The current CUDA `strata` executable was relinked after the session owner trace
change. All 23 selected Phase 3 memory, ownership, VMM, cache, graph,
conversation and PLE CTests passed serially, including the new
`session_loop_scratch_trace_test` and `ple_reader_selftest`. The suite ran under
the six-GiB supervisor with minimum host `MemAvailable` of 26,254,831,616 bytes
(24.45 GiB), with no cgroup memory pressure or OOM events.

The test only validates the mapped-host scratch allocation lifecycle. It does
not exercise the full legacy session-loop runtime route or change Strata's
default path. Full CTest output and supervisor telemetry are in `supervisor/`.

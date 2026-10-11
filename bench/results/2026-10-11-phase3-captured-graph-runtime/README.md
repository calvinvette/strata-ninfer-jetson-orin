# Generic captured-graph runtime trace — Orin — 2026-10-11

Added a CUDA runtime test for `strata::core::CapturedGraph`. It allocates a
stable device buffer, captures an asynchronous memset, successfully instantiates
and launches the graph, waits with a bounded timeout, and checks all 64 output
bytes. The CTest passed on Orin, and a direct run with
`STRATA_INTEGRATION_TRACE=1` emitted exactly one successful
`captured-graph/graph_instantiate` owner event alongside the verified replay.
The test binary SHA256 after adding an opt-in measurement pause is
`4f8e69b9820bca6113bcf30fe46ea671884d2c4000a4828b1091b6896e33e20c`.

The direct run's minimum sampled host `MemAvailable` was 26,434,379,776 bytes
(24.62 GiB), above the ordinary six-GiB floor. A repeated three-process NVMap
sampling experiment held each test's context, stable buffer and graph alive
around capture/instantiation. At 50 ms sampling, all three processes had exactly
94,216,192 bytes of process-owned NVMap backing in the stable pre-capture and
post-instantiation windows: measured delta 0 bytes in each. The capture trace
timestamps align with the NVMap sampler's monotonic clock. Minimum host
availability across these runs was 26,416,005,120 bytes (24.58 GiB). This rules
out a detectable net change in this counter for this single-node graph test at
that sampling resolution; it does not price CUDA allocations outside NVMap or
generalize to model graph pools.

The first sampler attempt raced the test and collected 139 empty rows after
process exit; it is retained in `nvmap-samples.jsonl` and `nvmap-supervisor/` as
a failed setup. The corrected run and three-process repeat are
`nvmap-samples-retry.jsonl`, `nvmap-supervisor-retry/` and
`nvmap-repeat-{1,2,3}/`. `STRATA_CAPTURED_GRAPH_TRACE_PAUSE_MS` adds optional
delays before capture and after instantiation for the independent sampler; it is
unset in ordinary CTest runs. The event's device remains `-1`. The test confirms
the generic wrapper's runtime and owner label, but does not exercise the model's
legacy session graph path or replace model-level graph accounting. CTest and
supervisor records are retained under `supervisor/` and `direct-supervisor/`.

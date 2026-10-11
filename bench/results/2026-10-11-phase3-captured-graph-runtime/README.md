# Generic captured-graph runtime trace — Orin — 2026-10-11

Added a CUDA runtime test for `strata::core::CapturedGraph`. It allocates a
stable device buffer, captures an asynchronous memset, successfully instantiates
and launches the graph, waits with a bounded timeout, and checks all 64 output
bytes. The CTest passed on Orin, and a direct run with
`STRATA_INTEGRATION_TRACE=1` emitted exactly one successful
`captured-graph/graph_instantiate` owner event alongside the verified replay.
The test binary SHA256 is
`96e395aa8b27a2cdf304e7ca8e196ec5fe6c84309b49a357e09f0ddf7c57b86a`.

The direct run's minimum sampled host `MemAvailable` was 26,434,379,776 bytes
(24.62 GiB), above the ordinary six-GiB floor. Both the CTest supervisor record
and the direct trace run are retained under `supervisor/` and
`direct-supervisor/`. The test confirms the generic captured-graph wrapper and
owner label execute at runtime; the event's device remains `-1`, and this test
does not measure CUDA graph executable or driver-pool bytes. It does not exercise
the model's legacy session graph path or replace model-level graph accounting.

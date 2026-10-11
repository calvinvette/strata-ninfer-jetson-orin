# Phase 3 owner and PLE test follow-up — Orin — 2026-10-10

The optional `--dump-layers` path now emits a `layer-dump-pinned-host` owner
allocation after its `cudaHostAlloc` succeeds and a matching free before
`cudaFreeHost`. The record uses device `-1`, so this diagnostic host buffer is
not added to device payload totals. It does not change allocation or output
behavior. The local ARM64 CUDA build succeeded (binary SHA256 is recorded in
the parent build tree); maestro1 rebuilt the same `src/program/generate.cpp`
for HIP with one job and its CLI help exited 0. maestro1 has no HIP runtime.
The SYCL engine uses a separate `sycl/src/program/generate.cpp`, which this
change does not touch.

A real owner event could not be produced with the available Orin artifacts.
The local runnable IQ pack requires `--spec >= 2`; `--dump-layers` disables the
token graph needed by speculation. Removing speculation is rejected for that
native pack. Both attempts failed during option validation before the layer
buffer allocation. Those unsupported combinations and raw command results are
preserved under `layer-dump-unsupported/`; they are not runtime failures of the
allocation itself. The owner event remains runtime-untested on this board.

The six-GiB-supervised Phase 3 batch passed 9 of 10 selected tests, including
`ple_parity` against the existing Q2_0 pack/shard, the native dense PLE key
check, segmented VMM, cache memory refusal, pinned fallback and shared-memory
tests. `ple_reader_selftest` failed two keepalive timing assertions in its
110-byte-row case, after the codec and 90-byte-row cases passed. An isolated
supervised rerun passed the full selftest. The batch's minimum `MemAvailable`
was 24.54 GiB; the isolated rerun's was 24.56 GiB. Treat the first result as a
transient timing-sensitive failure, not a clean batch pass. See raw outputs and
telemetry in `ple-memory-suite/` and `ple-reader-isolated/`.

The PLE artifact-aware seven-stage Q2_0 oracle remains covered by the earlier
[dedicated report](../2026-10-10-phase3-q2-ple-artifact-aware/README.md), which
uses real layer-1 weights and PLE table rows, synthetic hidden/history, and
passed all three tested tokens. No new model was downloaded. The repeated
owner parser and run-control unit suites passed 29 tests; `git diff --check`
also passed.

The owner trace still does not price graph executable/driver memory or cover
batch-slot session arenas. These remaining attribution gaps, plus broader
pressure and admission gates, keep Phase 3 open.

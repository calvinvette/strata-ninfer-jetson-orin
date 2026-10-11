# Phase 3 focused PLE and memory tests — Orin — 2026-10-10

The artifact-aware Q2_0 PLE block oracle and focused memory-owner tests were
rerun under `tools/integration/run_control.py` with the ordinary six-GiB
physical-availability floor. CTest passed all 10 selected tests in 47.11 s:

| Test | Result |
| --- | --- |
| `vmm_test` | pass |
| `native_dense_ple_key_test` | pass |
| `expert_cache_segmented_test` | pass |
| `ple_parity` | pass |
| `expert_cache_memory_test` | pass |
| `expert_cache_memory_refusal` | pass |
| `platform_memory_test` | pass |
| `pinned_fallback_test` | pass |
| `pinned_shared_test` | pass |
| `ple_reader_selftest` | pass |

Minimum observed host `MemAvailable` was 29,838,987,264 bytes (27.80 GiB).
The PLE artifact test uses real Q2_0 layer-1 weights and table rows with
synthetic hidden state/history; its mathematical and codec scope is described
in the [artifact-aware PLE report](../2026-10-10-phase3-q2-ple-artifact-aware/README.md).
This rerun confirms the existing focused checks; it does not add a new runtime
or product-path qualification.

The base user process namespace has no `/proc/self/io` or `/proc/1/io` entry,
and its leaf cgroup has no `io.stat`; ancestor counters aggregate unrelated
workloads. A later [seven-pair transfer confirmation](../2026-10-10-phase3-transfer-cgroupio-confirmation7/README.md)
used a temporary systemd scope with `IOAccounting=yes` and captured scoped
request read bytes. CUDA graph async-pool attributes still report zero for
Strata's graphs, while global free-memory deltas cannot attribute
executable/driver memory; see the
[graph-memory probe](../2026-10-10-phase3-graph-memory-probe/README.md).
Graph/driver attribution remains an open Phase 3 accounting gate, not a test
failure.

The supervised command, output, and telemetry are retained in `supervisor/`.
No model, build product, service state, or clock setting was changed.

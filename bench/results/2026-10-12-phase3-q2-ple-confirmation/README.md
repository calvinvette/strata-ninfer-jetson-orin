# Q2_0 PLE and memory-contract confirmation — Orin — 2026-10-12

The current candidate binary was rechecked against the artifact-aware Q2_0 PLE
oracle using the shard and generated PLE pack in `~/models/`. The supervised
`ple_parity --selftest` completed with zero failures and worst stage relative L1
error `1.148e-7`; the independent source-block round trip and native projection
checks passed. Minimum host `MemAvailable` was 26,282,037,248 bytes (24.47 GiB).
The exact command, stdout/stderr, and memory/tegrastats samples are retained in
`supervisor/`.

The same binary passed a serial 15-test CTest selection covering shared-memory
budget, conversation cache/memory, VMM, native dense PLE key, expert-cache
segmentation/admission/refusal, platform memory, session scratch tracing, PLE
parity/reader, convolution cache, and coupled draft tests. CTest reported 15/15
passed in 17.22 seconds. The six-GiB supervisor measured minimum host
`MemAvailable` of 26,285,715,456 bytes (24.47 GiB); raw output and telemetry are
under `memory-ctest/supervisor/`.

Integration Python unittest discovery passed 113/113 in 5.27 seconds. These
checks establish current-binary contract/test health, not hardware behavior
under system pressure, complete physical allocation ownership, or a Phase 3
exit. No default changed.

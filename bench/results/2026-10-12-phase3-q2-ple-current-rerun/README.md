# Q2_0 PLE and integration regression rerun — Orin — 2026-10-12

The current candidate passed a fresh, six-GiB-supervised artifact-aware PLE
self-test using the Q2_0 shard and PLE pack under `~/models`. All seven PLE
stages passed for three tokens; worst relative L1 error was `1.148e-7` and the
independent source-block and native projection checks passed. Minimum host
`MemAvailable` was 26,428,481,536 bytes (24.61 GiB). The exact command and raw
stdout, stderr, memory samples and tegrastats are in `ple/supervisor/`.

The serial Phase 3 memory/owner/PLE CTest selection passed 15/15 in 17.67
seconds. Minimum host availability was 26,418,937,856 bytes (24.60 GiB). The
exact expression and raw supervisor records are in `ctest/supervisor/`.
Integration Python unittest discovery passed 117/117 in 2.02 seconds; its
stdout is in `python/` (this short CPU suite was not separately supervised).

These checks reconfirm selected numerical and software contracts on the current
candidate. They do not qualify physical allocation ownership under pressure,
graph executable backing, task quality, or the full runtime hit/miss combination.
Phase 3 remains open and no default changed.

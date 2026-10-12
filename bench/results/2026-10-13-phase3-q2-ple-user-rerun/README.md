# Q2_0 PLE oracle and memory regression rerun — Orin — 2026-10-13

The current candidate passed a fresh supervised artifact-aware PLE parity
self-test using the Q2_0 PLE pack under `~/models/`. All seven numerical stages
passed for three tokens; worst stage relative L1 error was `1.148e-7`, source
block checks passed, and the native PLE value projection matched the independent
host oracle. Minimum host availability was 24.42 GiB; the six-GiB supervisor
floor was preserved.

The serial Phase 3 memory/owner/PLE CTest selection passed 15/15 in 16.53
seconds, with 24.45 GiB minimum host availability. Full integration Python
discovery passed 124/124 after adding exact-length held-out prompt checks to the
shared harness. Neither check changes the
runtime defaults or proves whole-model quality, pressure recovery, or complete
physical/graph backing. The exact commands, supervisor records, and outputs are
retained in this directory.

# Phase 3 owner and graph regression — Orin — 2026-10-11

The current native candidate passed a serial 19-test CTest selection under the
standard six-GiB physical-availability supervisor. Coverage includes shared
memory-budget arithmetic, conversation/cache memory and transfer, VMM, expert
cache allocation and refusal, native dense PLE reconstruction, the artifact-aware
Q2_0 PLE oracle, platform-memory reporting, captured-graph ownership, convolution
cache and conversation validation/snapshot/file paths.

All 19 tests passed (`ctest --test-dir build/integration/candidate
--output-on-failure -j1` with the recorded regular-expression selection). The
supervisor's minimum host `MemAvailable` was 26,352,754,688 bytes (24.53 GiB),
with no cgroup memory events. This validates the selected software contracts on
the current Orin binary; it is not model graph-pool pricing or active pressure
qualification. The legacy session/token graph classes remain untested because
the available pack requires native execution.

Raw CTest output, the supervisor record, memory samples and tegrastats are
retained under `supervisor/`. No defaults changed.

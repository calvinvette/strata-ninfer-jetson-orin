# Phase 3 accounting and owner regression — Orin — 2026-10-11

The current candidate passed all 15 selected CTests under the ordinary
six-GiB availability supervisor. This expanded the previous focused set with
shared-memory budget arithmetic, conversation-memory and conversation-cache
reservation behavior, per-layer expert-cache allocation, and convolution-state
cache coverage. The set also reran VMM, segmented cache, refusal/fallback,
platform admission, PLE oracle, and PLE reader tests.

Minimum sampled `MemAvailable` was 26,442,485,760 bytes (24.63 GiB). The test
process was sequential (`-j1`). The raw CTest output, supervisor record,
tegrastats and memory samples are retained in this directory.

This is unit/integration contract evidence. It does not price CUDA graph
executable or driver memory, nor close broader transfer/admission measurement
gates. No runtime defaults changed.

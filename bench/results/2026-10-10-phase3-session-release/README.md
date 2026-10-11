# Exploratory session backing teardown — Q2_0 Orin — 2026-10-10

The primary session arena, every split-stage arena, and batch-slot arenas now have explicit owners. Their destructors call `session_release` while the carved state is alive, select the owning device, free the backing, and emit a matching trace event. Batch arenas are also released before their `SessionState` objects when admission trims the slot count or disables batching. Primary allocation tracing now begins immediately after `cudaMalloc`, so a later `session_init` failure has a matching allocation event and cleanup.

This preliminary native CUDA build and Q2_0 serial/two-slot batch smoke passed under the six-GiB supervisor. It balanced primary and batch arena free events, but preceded a review of destructor member ordering and the final explicit teardown sequence. Treat its trace as exploratory; the [Oct 11 final teardown report](../2026-10-11-phase3-session-release/README.md) supersedes it.

The four session/checkpoint CTests passed: `conversation_split_failure_test`, `conversation_memory_test`, `conversation_snapshot_test`, and `conversation_validation_test`. Minimum availability was 26,317,148,160 bytes (24.50 GiB); see [the supervised CTest run](../2026-10-10-phase3-session-release-state-tests/).

The source and binary hashes for this preliminary version are superseded by the Oct 11 report. The layer-stage destructor still has no Orin runtime coverage because this host has one GPU and no layer-split stage; graph executable/driver memory attribution also remains open.

`../2026-10-10-phase3-session-release-final/` contains an additional Oct 10 smoke after the first member-ordering adjustment but before the final explicit cleanup sequence. Both Oct 10 logs are retained as exploratory; the Oct 11 report is the final evidence.

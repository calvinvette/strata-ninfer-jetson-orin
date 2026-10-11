# Phase 3 owner and memory regression — Orin — 2026-10-11

The current native candidate passed all 14 available selected CTests under the
ordinary six-GiB physical-availability supervisor. Coverage included shared
memory budget arithmetic, conversation/cache reservations and transfer,
segmented/per-layer expert cache, VMM, PLE key reconstruction, the artifact-aware
Q2_0 `ple_parity` oracle, and expert-cache allocation/refusal behavior. Tests ran
sequentially (`-j1`). Minimum sampled host `MemAvailable` was 26,409,766,912
bytes (24.60 GiB); the supervisor observed no cgroup memory events.

The Q2_0 PLE case uses the local pack and source GGUF shard configured in the
CTest manifest. This is repeatable operator and ownership-contract coverage,
not a full model execution or performance result. Native executable SHA256:
`3ed52e6e0f845415b8fb2f2c15577f4b90efe49be72e2866d0dc961dbb0c95b0`.
The raw CTest output, supervisor record, memory samples and tegrastats are
retained in `supervisor/`. No defaults changed.

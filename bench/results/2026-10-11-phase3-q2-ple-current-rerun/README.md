# Current-binary Q2_0 PLE parity rerun — Orin — 2026-10-11

The current CUDA candidate passed CTest `ple_parity` with the local Q2_0
artifact-aware pack and matching native GGUF PLE shard. The test ran under the
standard six-GiB physical availability supervisor; minimum `MemAvailable` was
26,476,240,896 bytes (24.66 GiB), with no cgroup memory events. This is the
focused operator parity check, not full-model quality or serving evidence.

The exact command is in `result.json`; CTest output and raw supervisor
telemetry are retained in this directory. Model files remain under
`/home/calvin/models/`.

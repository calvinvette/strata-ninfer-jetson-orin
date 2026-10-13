# IQ1_M service reload and teardown check

This Phase 7 check ran three fresh loopback services using the selected opt-in
IQ1_M Q6 warp-dequant, accepted-only MTP4, FP16 KV profile at 8K context. Each
cycle completed one distinct 512-token warmup and one measured request of
exactly 512 prompt and eight generated tokens, then stopped its server before
the next cycle. Each cycle used a unique loopback port. The harness required the
measured request to pass, the listener to close, and the engine PID to disappear
before advancing.

All three cycles passed. The measured output digest was identical in every
cycle. After each stop the listener was available for rebinding and no Strata
engine process remained. The 28-GiB supervisor recorded 13.11 GiB minimum host
availability and 12.77 GiB minimum effective admission headroom; cgroup `oom`,
`oom_kill`, `high`, and `max` counters stayed zero. CPU/GPU clocks were sampled
under dynamic policy; EMC rate readback was denied and energy was not measured.

This verifies three sequential model loads, requests and teardowns for the one
profile and short workload. It does not test simultaneous services, repeated
reload over a longer soak, other model formats or concurrent-request
isolation.

An initial invocation was interrupted during service startup because it was
launched without the required memory supervisor. No request was made and no
service remained; its partial files are retained under
`attempt-01-unsupervised-interrupt/` and excluded. The measured rerun is the
top-level `cycle-01` through `cycle-03` set. Model assets stayed in `~/models/`.

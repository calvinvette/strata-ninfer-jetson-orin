# Broad CPU SwiGLU operation-order probe — Orin — 2026-10-20

This same-service delayed-control/adaptive pair tests the reciprocal sigmoid
operation order for all enabled CPU Q8_1 native expert routes. It uses the
pinned Coder IQ1_M GGUF at revision
`5348543e0147355ac9cbcb031184a3546350988e`, binary SHA256
`6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`, seed
`20261036`, and the established short-512 / long-2048 / short-recovery workload
with 64 generated tokens per request. Arm order was adaptive-cap8, then
delayed-control. The full runner inputs, raw traces, service logs and
supervisor telemetry are retained beside this report.

Both services passed their 28-GiB supervision with at least 14.01 GiB host and
admission availability and zero cgroup pressure/OOM events. Delayed control
recovered exactly: all 64 recovery token IDs matched the initial short request
and its recorded state keys were unchanged. Adaptive migration produced 40/64
different recovery token IDs and changed GDN, PLE, residual-tail, pooled, KV
and PLE-history fingerprints. Its raw layer-32 commit-state records at positions
518–520 match the service's logged GDN ordinal-24 hashes. This operation-order
change is therefore rejected as a broad recovery correction, even though the
isolated expert parity check below is exact.

The result is a diagnostic failure, not a speed or quality comparison. The
opt-in arithmetic is not suitable for general promotion. See the targeted
layer-31-only follow-up in the sibling
[`adaptive-prefix8-layer31-silu-check`](../adaptive-prefix8-layer31-silu-check/README.md).

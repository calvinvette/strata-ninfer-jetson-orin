# Layer-31-only CPU SwiGLU operation-order probe — Orin — 2026-10-20

This same-service delayed-control/adaptive pair restricts the reciprocal
sigmoid operation order to `iq3_xxs/iq4_nl@layer=31`, where the layer-31,
expert-22 CPU/CUDA mismatch had been localized. It uses the pinned Coder IQ1_M
GGUF at revision `5348543e0147355ac9cbcb031184a3546350988e`, binary SHA256
`6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`, seed
`20261037`, and the short-512 / long-2048 / short-recovery workload with 64
generated tokens per request. The randomized order was delayed-control, then
adaptive-cap8. `campaign.json` records model shard hashes and runner hashes;
raw committed states, per-layer service hashes, route traces and supervisor
telemetry are retained in each arm directory.

The delayed control recovered exactly, with no changed state keys. Adaptive
initial and recovery output token IDs also matched, but its committed layer-32
state first differed at captured position 518: all 786,432 recurrent values
and all 30,720 convolution-history values differed (relative recurrent L2
`0.03009`). Positions 519 and 520 also differed. Raw state records at all three
positions match the service's logged GDN ordinal-24 hashes. Both supervised
arms passed with minimum host/admission availability of 14.21 GiB (delayed)
and 14.18 GiB (adaptive), with no cgroup pressure/OOM events.

The same captured layer-31 activation was independently checked after the
operation-order change. CPU and CUDA input Q8_1 blocks, all 1,920 gate and 1,920
up dot outputs, all 60 post-SwiGLU hidden Q8_1 blocks, and all 7,680 down
projection output words matched bitwise. This establishes exact parity for
that expert input and route, but the service pair shows that fixing this seam
alone does not establish adaptive accepted-state recovery. The candidate is
not a migration fix and has no performance qualification.

The command and full raw output are retained in the sibling
[`operator-checks/layer31-position519`](../operator-checks/layer31-position519/README.md)
and in this pair's `campaign.json` and arm directories.

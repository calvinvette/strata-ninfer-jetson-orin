# Position-518 adaptive route trace with layer-31-only CPU mirror — Orin — 2026-10-20

This shortened same-service pair captures every MoE dispatch at accepted
position 518 while the reciprocal-sigmoid CPU mirror is restricted to
`iq3_xxs/iq4_nl@layer=31`. It uses the Coder IQ1_M snapshot at revision
`5348543e0147355ac9cbcb031184a3546350988e`, binary SHA256
`6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`, seed
`20261038`, and the established short-512 / long-2048 / short-recovery sequence
with 12 generated tokens per request. Arm order was delayed-control, then
adaptive-cap8. The full traces, raw state dumps, logs, request records and
supervisor telemetry are retained in the arm directories.

Delayed control recovered exactly: all 12 output IDs, per-layer inputs and
owners, and captured layer-32 state matched between the first and recovery
requests. Adaptive output IDs also matched, but layer-32 recurrent state and
convolution history already differed at the first captured endpoint, position
518 (relative recurrent L2 `0.03075`). Its first captured input activation
difference was layer 2, expert IDs first differed at layer 3, and owner
placement first differed at layer 6; owner flips continued through many later
layers, including layer 31. This shows that the layer-31 expert-22 arithmetic
seam is not the earliest observed divergence in this sequence. The trace
localizes boundaries but does not identify the operation that caused them.

Both supervisors passed with 14.19 GiB (delayed) and 14.31 GiB (adaptive)
minimum host/admission availability and zero cgroup pressure/OOM events. Raw
layer-32 state records match the service's logged GDN ordinal-24 hashes. This
is correctness localization, not a state migration fix or performance result;
Phase 5 remains open.

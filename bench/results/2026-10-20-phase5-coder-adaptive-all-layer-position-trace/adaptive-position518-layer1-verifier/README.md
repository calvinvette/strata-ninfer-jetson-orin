# Layer-1 verifier check at the position-518 adaptive boundary — Orin — 2026-10-20

This randomized same-service pair captured all MoE dispatch inputs at position
518 and layer-1 verifier routes, expert contributions and combined output. It
uses the Coder IQ1_M snapshot at revision
`5348543e0147355ac9cbcb031184a3546350988e`, binary SHA256
`6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`, seed
`20261039`, and short-512 / long-2048 / short-recovery requests with 12 output
tokens each. The layer-31 reciprocal-SiLU CPU mirror remained restricted to
`iq3_xxs/iq4_nl@layer=31`. The campaign, verifier captures, dispatch traces,
comparisons, service logs and telemetry are retained here.

Delayed control was exact: its 12 initial/recovery tokens, all layer inputs,
expert IDs and owners, and layer-1 verifier results matched. Adaptive output
tokens still matched, but its state fingerprint changed for GDN, residual
tail, pooled, and KV state. At layer 1, router IDs and weights matched, all
expert contributions were bit-identical, and both shared and combined MoE
outputs were exact. The first changed MoE input was at layer 2 (all 2,560
values; relative L2 `0.001581`); expert IDs first differed at layer 3 and
owner placement at layer 6. The route trace alone localizes the first changed
activation, while the layer-1 verifier capture excludes that layer's MoE
contribution as its source. Post-combine residual/hyper-connection and the
layer-2 GDN transition remain to be separated.

Both services passed supervision with at least 14.22 GiB (adaptive) and 14.29
GiB (delayed) minimum host/admission availability and zero cgroup pressure/OOM
events. This is a correctness localization, not a fix or performance claim;
Phase 5 remains open.

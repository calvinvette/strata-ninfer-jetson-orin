# Layer-21 GDN and residual boundary at position 534 — Orin — 2026-10-22

This supervised adaptive-only replay repeated the pinned 128-token
short→long→short Coder IQ1_M sequence and captured layer-21 GDN intermediates,
pre/post GDN state, and residual/hyperconnection fields around the layer-21 to
layer-22 seam at position 534. The initial and recovery requests used the same
token 3155.

All ten captured GDN intermediates (`x`, `qkv`, `h`, `gate`, `beta`, `z`, `y`,
`gdn_out`, `ffn_x`, `ffn_y`) were bit-identical. The pre/post committed GDN
state was also bit-identical. Every captured residual/hyperconnection field
was exact: after layer 21, before and after layer 22's first read, including
`R`, `bo`, `inj2`, and captured `xn`. This complements the prior exact layer-21
MoE rows and outputs. Yet the separate all-layer MoE-input capture showed the
first changed tensor at layer 22 (`mixed`/router input). Thus the currently
observed mismatch lies between these captured exact layer-21/first-read
values and layer 22's router input. The current probes do not expose the
specific intermediate responsible; we should inspect layer 22's fused
GR-read outputs (`lo`, `rs`, `inject_out`, `mixed`, and `xn`) before making a
causal claim.

The run completed all three 128-token requests in 594.1 seconds. Minimum
host/admission availability was 14.13 GiB, above the six-GiB floor; cgroup
memory-event counters remained zero. CPU/GPU clocks were sampled dynamically,
EMC readback was unsupported, and energy was not measured. Raw captures and
supervisor logs remain local; compact comparison JSON files are alongside this
report. These timings are diagnostic only.

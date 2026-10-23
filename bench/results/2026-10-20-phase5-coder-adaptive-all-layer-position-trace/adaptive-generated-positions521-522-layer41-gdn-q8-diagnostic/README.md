# Positions 521–522 layer-41 GDN state capture — Orin — 2026-10-20

This supervised same-seed pair used the pinned Coder IQ1_M model, the all-layer
Q8_1 selector, prompt cache disabled, and the current candidate binary. It
captured all verifier MoE inputs plus layer-41 GDN intermediates and raw
pre/post state at generated positions 521 and 522. Both arms passed; minimum
host/admission availability was 14.14 GiB adaptive and 14.23 GiB delayed, with
zero cgroup memory events.

At position 521, adaptive initial-to-intermediate layer-41 raw pre-state is
bit-identical (all 786,432 recurrent and 10,240 convolution-history values).
The GDN `x` field is the first differing intermediate and the post-state then
differs in 785,998 recurrent and all 10,240 convolution-history values. At
position 522, the pre-state already differs by 785,998 recurrent and all
10,240 convolution-history values; `h` is the first differing intermediate.
The raw post-state hashes match service GDN ordinal 31 for every captured
request. Intermediate-to-recovery, recovery-to-continuation, and all delayed
control transitions are exact at both positions.

The all-layer verifier input capture first differs at layer 40 at position
521 and layer 41 at position 522. QSA state hashes at model layers 43 and 47
change during adaptive initial-to-intermediate at both positions; delayed
control stays exact. This shows layer-41's state change is already present by
its position-522 pre-state, and at position 521 begins during layer-41 GDN
processing after the differing `x` input. A separate [position-521 layer-40
residual capture](../adaptive-generated-position521-layer40-boundary-q8-pair/README.md)
shows the boundary values after layer 40 already differ, so the layer-41 GDN
input mismatch is downstream of that earlier boundary change. The exact
layer-40 contribution is the next capture target. These results localize a
correctness divergence; they are not a migration fix or performance result.

Reproduce the analysis from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer41_gdn.py \
  --run-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-positions521-522-layer41-gdn-q8-diagnostic \
  --positions 521 522
```

Raw verifier inputs, GDN intermediates, state captures, service logs and
supervisor telemetry are retained under each arm. The parsed comparison is in
`layer41-gdn-analysis.json`; verifier and QSA comparisons are in
`verifier-input-analysis.json` and `qsa-state-analysis.json`.

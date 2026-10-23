# Layer-5 owner trace after the layer-2 mirror — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used seed `20261079`, the
layer-2 mirror selector, and the pinned Coder IQ1_M GGUF at revision
`5348543e0147355ac9cbcb031184a3546350988e`. Candidate binary SHA256:
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. The
same-service workload was 512/2,048/512 tokens with 12 generated tokens per
request under separate 28-GiB supervisors.

Delayed-control recovery matched initial across selected activations, routes,
outputs and accepted state. Adaptive recovery still differed at all 12 token
IDs and every accepted-state/GDN prefix. Positions 506–511 first differ at
activation layer 6; position 505 first differs at layer 27. At layer 5,
positions 506–511 keep expert IDs and router weights fixed while IQ2_S/IQ4_NL
expert 26 moves CPU-to-GPU and is the only routed row that changes. The
combined MoE output changes at all six positions. Layer-5 GDN first differs
at `ffn_y` at positions 506–511; position 505 is exact. The captured raw
layer-5 recurrent and convolution state at position 511 is exact across
initial/recovery.

An independent single-row `native_expert_parity` run used the exact captured
layer-5 activation at position 506. The CPU and GPU oracle outputs each match
their corresponding service row bit-for-bit; CPU/GPU outputs differ by 1.4092%
relative L2. This joins the owner change to the service arithmetic for one
position and expert. It does not establish the cause of adaptive residency,
restore full request-state parity, or show a quality/performance winner. The
layer-5 rule remains opt-in; a follow-up now tests whether it restores this
boundary.

Retained comparisons are `selected-position-analysis.json`,
`layer5-moe-analysis.json`, `layer5-gdn-analysis.json`,
`layer5-state-analysis.json`, and
`expert26-position506-oracle/oracle-join.json`. The standalone oracle input and
operator dumps are beside the join report. Both supervisors passed with
minimum host/admission availability 14.17 GiB for delayed-control and 14.31
GiB for adaptive-cap8, above the six-GiB floor, with zero cgroup memory events.
Clocks were observed but not controlled; energy was not attributed.

This is a correctness localization for one model, workload and set of
positions, not timing or task-quality evidence. Reproduce the service pair
with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261079 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=2,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15,iq3_xxs/iq4_nl@layer=16,iq2_s/iq4_nl@layer=19,iq2_s/iq4_nl@layer=24' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 5 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 5 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 5 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 5 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-2-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer5-boundary-pair
```

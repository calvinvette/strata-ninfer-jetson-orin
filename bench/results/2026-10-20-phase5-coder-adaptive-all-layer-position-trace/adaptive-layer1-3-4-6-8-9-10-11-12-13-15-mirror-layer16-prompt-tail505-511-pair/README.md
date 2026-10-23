# Layer-16 owner rows after the layer-15 mirror — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. It used
the 512/2,048/512 short/long/recovery sequence and 12 generated tokens. The
adaptive arm used exact format-and-layer Q8_1 rules through layer 15. Arm order
was adaptive then delayed control.

At layer 16, adaptive initial and recovery inputs, routes, and router weights
match at all selected positions 505–511. Four expert owners migrate CPU-to-GPU:
experts 118, 220, 39, and 30. GGUF tensor headers identify every row as
IQ3_XXS/IQ4_NL. The [21 same-input native expert oracle rows](layer16-owner-oracles.json)
match the service CPU and GPU outputs bit-for-bit. Relative-L2 differences
range from 1.23% to 1.64%. The combined layer-16 MoE output changes at all seven
positions; layer-16 GDN first differs at `ffn_y` at all seven positions.

Raw layer-16 recurrent and convolution state at position 511 matches between
adaptive initial and recovery, and the accepted raw commit at 511 matches
service GDN ordinal 12. Delayed control remains exact. Adaptive recovery IDs
and all 12 accepted-prefix states differ; the first captured activation
difference moves to layer 17. The [next pair](../adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-mirror-layer17-prompt-tail505-511-pair/README.md)
adds the layer-16 IQ3_XXS/IQ4_NL rule and checks that boundary.

Both supervised arms passed with at least 14.23 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. This is correctness
localization for one model and workload, not a timing comparison or complete
state-transaction qualification. Phase 5 remains open.

Reproduce the paired run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261070 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 16 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 16 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 16 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 16 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-15-mirror-layer16-prompt-tail505-511-pair
```

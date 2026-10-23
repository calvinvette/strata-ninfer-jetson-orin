# Layer-24 owner row after the layer-19 mirror — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. It used
the 512/2,048/512 short/long/recovery sequence and 12 generated tokens. The
adaptive arm used exact format-and-layer Q8_1 rules through layer 19. Arm order
was adaptive then delayed control.

At layer 24, routes and router weights match across adaptive initial and
recovery at positions 505–511. Expert 173 (IQ2_S/IQ4_NL) changes CPU-to-GPU at
positions 507 and 511; its two [single-row native oracle joins](expert173-layer24-owner-oracle.json)
match both service owner rows bit-for-bit. Its changed rows make the combined
MoE output differ at those positions, and layer-24 GDN first differs at
`ffn_y` there. Other captured positions are exact. Raw recurrent and
convolution state at 511 matches across initial/recovery, and the accepted raw
commit matches service GDN ordinal 18.

Adaptive recovery token IDs match for all 12 tokens, but all accepted-prefix
state records still differ. The first captured activation difference occurs
at layers 25, 27, or 28 by position. The trace also identifies expert 213
(IQ3_XXS/IQ4_NL) changing owner at layer 26, position 505, and expert 36
(IQ2_S/IQ4_NL) at layer 28, position 506. The next pair adds the layer-24 rule
and captures layer 25. Delayed control remains exact.

Both supervised arms passed with at least 14.20 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. This is correctness
localization for one model and workload, not a timing comparison or complete
state-transaction qualification. Phase 5 remains open.

Reproduce the paired run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261074 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15,iq3_xxs/iq4_nl@layer=16,iq2_s/iq4_nl@layer=19' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 24 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 24 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 24 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 24 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-mirror-layer24-prompt-tail505-511-pair
```

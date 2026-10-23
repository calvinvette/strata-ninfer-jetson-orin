# Layer-12 mirror and layer-13 owner trace — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. It used
the 512/2,048/512 short/long/recovery sequence and 12 generated tokens. The
adaptive arm added the exact IQ3_XXS/Q2_0 mirror at layer 12 to the earlier
layer rules. Arm order was adaptive then delayed.

With the layer-12 mirror, all ten captured GDN intermediate fields at model
layer 12 are bit-identical between adaptive initial and recovery requests at
positions 505–511. Raw recurrent and convolution state before and after token
271 at position 511 is also bit-identical. The next layer-13 MoE inputs, routes,
and router weights match at all seven positions, but expert 147 moves CPU-to-GPU
at every position and its row changes. GGUF headers identify its weights as
IQ2_S/Q2_0. Independent single-row `native_expert_parity` oracles match the
service CPU and GPU outputs at all seven positions; each row changes in all
2,560 values, with relative-L2 differences from 1.04% to 1.49%. The first
captured activation difference is layer 14.

Adaptive recovery returns the same 12 token IDs as the initial short request,
but all 12 accepted-prefix state records differ. Service GDN hashes first
differ at ordinal 11 (model layer 14) at accepted position 511, then continue
to differ. The delayed control remains exact. This localizes the next owner-
dependent row after fixing layer 12; it does not establish that the layer-13
row is the sole cause of the later persistent-state differences.

Both supervised arms passed with at least 14.22 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. This is correctness
localization for one model and workload, not a timing comparison or a complete
state-transaction result. Phase 5 remains open.

The [layer-13 expert oracle](layer13-expert147-owner-oracle.json) records the
same-input service joins. Raw captures and one-row oracle dumps are retained
beside it. Reproduce the paired run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261067 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 13 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 12 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 12 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 12 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-mirror-layer13-prompt-tail505-511-pair
```

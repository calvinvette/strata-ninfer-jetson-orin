# Layer-16 mirror and next owner trace — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. It used
the 512/2,048/512 short/long/recovery sequence and 12 generated tokens. The
adaptive arm used exact format-and-layer CPU Q8_1 rules through layer 16. Arm
order was delayed control then adaptive.

With the layer-16 mirror, selected layer-16 GDN intermediates and raw recurrent
and convolution state at position 511 match bit-for-bit between adaptive
initial and recovery. The accepted raw commit at position 511 matches service
GDN ordinal 12. Layer-17 verifier routes, router weights and combined MoE
outputs also match at positions 505–511. The first captured activation
difference moves to layer 20.

Adaptive recovery token IDs match the initial short request for all 12 tokens,
but all 12 accepted-prefix state records differ. At accepted prefix index 8,
GDN ordinals 15–35 first differ, corresponding to model layer 20 onward. The
selected dispatch trace shows expert 221 (IQ2_S/IQ4_NL) changing CPU-to-GPU at
layer 19 at positions 505, 506, 507, and 511, with identical inputs, routes,
and router weights. A direct layer-19 verifier and same-input oracle pair is
the next localization step. Delayed control remains exact.

Both supervised arms passed with at least 14.12 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. This is correctness
localization for one model and workload, not a timing comparison or complete
state-transaction qualification. Phase 5 remains open.

Reproduce the paired run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261071 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15,iq3_xxs/iq4_nl@layer=16' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 17 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 16 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 16 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 16 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-mirror-layer17-prompt-tail505-511-pair
```

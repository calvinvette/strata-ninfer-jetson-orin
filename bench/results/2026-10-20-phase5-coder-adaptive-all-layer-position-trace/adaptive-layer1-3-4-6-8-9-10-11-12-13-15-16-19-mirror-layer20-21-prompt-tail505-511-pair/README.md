# Layer-19 mirror and layer-20 state trace — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. It used
the 512/2,048/512 short/long/recovery sequence and 12 generated tokens. The
adaptive arm used exact format-and-layer Q8_1 rules through layer 19. Arm order
was adaptive then delayed control.

At layer 19, expert 221 (IQ2_S/IQ4_NL) changes CPU-to-GPU at positions 505,
506, 507, and 511. The [four single-row native expert oracles](../adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-mirror-layer19-20-prompt-tail505-511-pair/expert221-layer19-owner-oracle.json)
match the service CPU and GPU rows bit-for-bit on identical activations, routes,
and weights. The layer-19 rule makes all selected layer-20 GDN intermediates
and raw recurrent/convolution state at position 511 exact across adaptive
initial/recovery. The accepted raw commit at position 511 matches service GDN
ordinal 15. Layer-21 routes, router weights, and combined MoE outputs also
match at all selected positions.

Adaptive recovery token IDs match for all 12 tokens, but all 12 accepted-prefix
state records still differ. The first selected activation difference now
appears at layers 25–28 depending on prompt-tail position. The dispatch trace
shows IQ2_S/IQ4_NL expert 173 changing CPU-to-GPU at layer 24 at positions 507
and 511; later owner flips include expert 213 at layer 26, position 505, and
expert 36 at layer 28, position 506. A layer-24 MoE/GDN capture is the next
localization step. Delayed control remains exact.

Both supervised arms passed with at least 14.22 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. This is correctness
localization for one model and workload, not a timing comparison or complete
state-transaction qualification. Phase 5 remains open.

Reproduce the paired run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261072 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15,iq3_xxs/iq4_nl@layer=16' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 19 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 20 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 20 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 20 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-mirror-layer19-20-prompt-tail505-511-pair
```

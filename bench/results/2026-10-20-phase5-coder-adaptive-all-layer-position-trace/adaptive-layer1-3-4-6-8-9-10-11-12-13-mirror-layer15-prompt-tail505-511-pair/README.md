# Layer-15 expert-250 owner row — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. It used
the 512/2,048/512 short/long/recovery sequence and 12 generated tokens. The
adaptive arm used exact format-and-layer Q8_1 rules through layer 13. Arm order
was adaptive then delayed control.

At layer 15, the verifier routes and router weights match at positions 505–511.
Expert 250, with IQ2_S/IQ4_NL weights, changes CPU-to-GPU only at position 505.
Its combined MoE output changes there; all other selected positions match.
The [same-input native expert oracle](expert250-position505-owner-oracle.json)
matches the service CPU and GPU rows bit-for-bit on that captured activation.
All 2,560 output values differ between CPU and GPU, with relative L2 `1.4442%`.

The first captured activation difference is layer 16 at all seven positions.
Adaptive recovery token IDs and all 12 accepted-prefix state records differ;
delayed control remains exact. This identifies another local owner-dependent
row without establishing that it alone explains the persistent-state change.
The next pair adds the exact layer-15 mirror and captures layer 16.

Both supervised arms passed with at least 14.22 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. This is correctness
localization for one model and workload, not a timing comparison or complete
state-transaction qualification. Phase 5 remains open.

Reproduce the paired run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261069 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 15 --verify-moe-positions 505,506,507,508,509,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-mirror-layer15-prompt-tail505-511-pair
```

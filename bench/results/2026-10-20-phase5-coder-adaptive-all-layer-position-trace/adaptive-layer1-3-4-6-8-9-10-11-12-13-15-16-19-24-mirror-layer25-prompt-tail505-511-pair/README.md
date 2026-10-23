# Layer-24 mirror context-shift probe — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. It used
the 512/2,048/512 short/long/recovery sequence and 12 generated tokens. The
adaptive arm added the layer-24 IQ2_S/IQ4_NL rule to the earlier exact-pair
rules. Both supervised arms completed successfully.

This probe is **inconclusive for the intended layer-24 localization**. With
the added rule, the adaptive initial/recovery dispatch inputs and router IDs or
weights already differ by captured layer 3 at all positions 505–511. The
layer-24 GDN input `x` differs at all seven positions, and layer-25 verifier
routes/weights differ at all seven positions. Adaptive recovery IDs differ at
all 12 tokens. Raw layer-24 recurrent state at accepted position 511 differs
in 786,431 of 786,432 values before the selected token and 786,432 afterward.
Delayed control remains exact. Since the adaptive histories no longer share
the same upstream dispatch input, this pair cannot attribute the change to the
layer-24 expert-173 row. Preserve it as a context-shift result; do not treat the
layer-24 mirror as a localized fix.

Both supervised arms passed with at least 14.16 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. The result is correctness
diagnostic evidence for one model and workload, not a timing comparison.

Reproduce the run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261075 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15,iq3_xxs/iq4_nl@layer=16,iq2_s/iq4_nl@layer=19,iq2_s/iq4_nl@layer=24' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 25 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 24 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 24 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 24 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer25-prompt-tail505-511-pair
```

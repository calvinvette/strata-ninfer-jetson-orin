# Layer-12 IQ3_XXS/Q2_0 owner rows — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. The candidate binary SHA256 is
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran the 512/2,048/512 short/long/recovery sequence with 12 generated
tokens. The adaptive arm used exact format-and-layer Q8_1 CPU mirror rules at
layers 1, 3, 4, 6, 8, 9, 10, and 11. Arm order was adaptive then delayed.

The layer-12 verifier routes and router weights match at positions 505–511.
Layer-12 expert 73 changes CPU-to-GPU at positions 505 and 507; expert 141
changes at 507 and 511. GGUF tensor headers identify both as IQ3_XXS/Q2_0.
Independent `native_expert_parity` checks on the exact serialized activations
match the service CPU and GPU rows for all four owner changes. CPU/GPU row
relative-L2 differences range from 1.32% to 1.50%. The separately retained
batched-width probe did not join its second output row to the service row for
73@507 and 141@511; those cells are marked inconclusive, and single-row
rechecks establish the valid oracle joins. The raw batch probe remains in
`layer12-owner-oracle-batched-probe.json` and is excluded from conclusions.

Despite these row differences, the selected layer-12 raw GDN pre/post recurrent
and convolution states at position 511 match bit-for-bit between adaptive
initial and recovery requests. Layer-12 GDN intermediates first differ at
`ffn_y` for positions 505, 507, and 511; all other captured positions and
fields match. The 12-token recovery differs at six token IDs, beginning at
position 517, while the delayed control is exact. Thus the layer-12 evidence
localizes changed arithmetic but does not by itself explain the accepted-state
divergence.

Both supervised arms passed with at least 14.14 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. This is correctness
localization for one model and workload, not a timing comparison or a complete
state-transaction result. Phase 5 remains open.

Reproduce the paired run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261066 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 12 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 12 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 12 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 12 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-combined-mirror-layer12-prompt-tail505-511-pair
```

Raw service captures, oracle inputs and outputs, supervisor records, state
dumps, and the inconclusive batched probe are retained alongside this report.

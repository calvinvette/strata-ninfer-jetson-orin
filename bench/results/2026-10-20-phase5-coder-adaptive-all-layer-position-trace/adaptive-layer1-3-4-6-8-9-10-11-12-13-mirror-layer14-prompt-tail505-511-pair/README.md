# Layer-13 mirror and layer-14 state trace — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. It used
the 512/2,048/512 short/long/recovery sequence and 12 generated tokens. The
adaptive arm used exact format-and-layer CPU Q8_1 rules through layer 13. Arm
order was delayed control then adaptive.

At positions 505–511, layer-14 routes, router weights, combined MoE outputs,
GDN intermediates, and raw recurrent/convolution state at 511 match bit-for-bit
between adaptive initial and recovery. The accepted raw commit at 511 also
matches service GDN ordinal 11. The selected dispatch trace's first activation
difference is layer 16 at each position. It shows one owner flip at layer 15:
expert 250, IQ2_S/IQ4_NL, at position 505. A direct verifier capture and exact
service-row oracle for this layer-15 row are the next localization step.

The adaptive short-recovery IDs differ at all 12 generated positions, while
delayed control is exact. At accepted prefix index 8, all 36 per-layer GDN
fingerprints differ. The exact layer-14 local boundary therefore does not
resolve the earlier state divergence. Raw commit captures at prompt-tail
positions 506, 508 and 510 have no accepted-prefix service hashes; the service
cross-check is valid only for accepted position 511. The unsupported checks at
those prompt positions are not counted as failures or evidence.

Both supervised arms passed with at least 14.17 GiB available RAM and zero
cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed but not
controlled; energy was not attributed to requests. This is correctness
localization for one model and workload, not a timing comparison or complete
state-transaction qualification. Phase 5 remains open.

Reproduce the paired run from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261068 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 14 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 14 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 14 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 14 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-mirror-layer14-prompt-tail505-511-pair
```

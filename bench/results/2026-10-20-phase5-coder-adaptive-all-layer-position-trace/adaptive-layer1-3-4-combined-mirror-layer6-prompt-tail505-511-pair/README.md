# Layer-6 expert-110/162 migration at prompt-tail positions — Orin — 2026-10-20

This randomized adaptive/delayed-control pair used the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M model at revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran the same 512-token short, 2,048-token long, and 512-token recovery
requests, each limited to 12 generated tokens. Arm order was adaptive then
delayed control. The adaptive arm enabled the opt-in CPU Q8_1 mirror at model
layers 1, 3, and 4, using exact IQ2_S/Q2_0 or IQ2_S/IQ4_NL rules.

At layer 6, positions 506–511 have identical input activations, expert IDs,
and router weights across adaptive initial and recovery requests. Experts 110
and 162 each change CPU-to-GPU ownership at all six positions. Both expert
rows differ across all 2,560 values, and the combined MoE output differs across
all 2,560 values. Position 505 is exact at this layer. The first changed GDN
intermediate is `ffn_y` at positions 506–511. Layer-6 pre/post recurrent and
convolution state at position 511 and committed state at positions 506, 508,
510, and 511 remain bit-identical across adaptive requests. The delayed-control
arm stays exact in routes, outputs, accepted token IDs, and service GDN hashes.

Independent same-input `native_expert_parity` oracles at position 511 matched
the service's CPU and GPU rows exactly for both experts. Their default CPU/GPU
relative-L2 differences are `0.01423` (expert 110) and `0.01428` (expert 162).
With the opt-in `STRATA_NATIVE_CPU_Q8_1_DOT=iq2_s/iq4_nl@layer=6` selector, both
oracle CPU/GPU rows are bit-identical (0/2,560 values differ). This identifies
the owner-dependent operator rows as the direct source of the layer-6 output
difference for this captured input; it does not qualify longer-chain state
parity.

In this arm configuration, the first observed adaptive dispatch-activation
difference remains at model layer 7 for positions 506–511 and at layer 10 for
position 505. The first changed service GDN hash is ordinal 6 at accepted
endpoint 511. Adaptive recovery has six differing token IDs, first mismatching
at position 517 (initial ID 264, recovery ID 819), and changed terminal
fingerprints in `gdn`, `ple`, `tail`, `pooled`, `pooled_full`, `kv`, and
`ple_prev`. Both arms passed supervision; minimum host/admission availability
was 14.17 GiB for adaptive and 14.18 GiB for delayed control. Across 186 and
190 memory samples, cgroup `high`, `max`, `oom`, and `oom_kill` counters were
zero. Clocks were observed but not controlled, and energy was not attributed
to requests.

The next paired test adds the layer-6 Q8_1 mirror and captures layer 7. This is
correctness localization for one model and workload, not a performance result
or completed adaptive migration qualification. Phase 5 remains open.

Reproduce the pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261058 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 6 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 6 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 6 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 6 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-combined-mirror-layer6-prompt-tail505-511-pair
```

Raw captures, two expert oracle outputs, comparisons, service logs, memory
samples, and supervisor records are retained here.

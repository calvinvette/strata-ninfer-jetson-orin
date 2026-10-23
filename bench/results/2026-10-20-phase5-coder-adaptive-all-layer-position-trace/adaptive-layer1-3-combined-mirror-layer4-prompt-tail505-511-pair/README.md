# Layer-4 expert-153 migration at prompt-tail positions — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M at revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran 512-token short, 2,048-token long, and short recovery requests, each
limited to 12 generated tokens. Randomized arm order was delayed control then
adaptive. The adaptive arm enabled the opt-in CPU Q8_1 mirror for
`iq2_s/q2_0@layer=1` and `iq2_s/iq4_nl@layer=3`.

At model layer 4, positions 505, 508, and 509 have identical input activation,
expert IDs, and router weights, but expert 153 changes CPU-to-GPU ownership.
Its row changes in all 2,560 values, and the combined MoE output changes in all
2,560 values. Positions 506, 507, 510, and 511 have identical expert rows and
combined outputs. The captured layer-4 GDN intermediates differ only in `ffn_y`
at the three changed positions; the layer-4 recurrent and convolution states at
position 511 and committed states at 506, 508, 510, and 511 remain bitwise
identical across adaptive initial/recovery. Delayed control is exact across all
captured positions.

An independent same-input `native_expert_parity` oracle at positions 505, 508,
and 509 matches each service CPU row and GPU row exactly. The CPU/GPU relative-L2
differences are `0.01553`, `0.01430`, and `0.01670` respectively. At position
505, enabling `STRATA_NATIVE_CPU_Q8_1_DOT=iq2_s/iq4_nl@layer=4` makes the oracle
CPU and GPU expert-153 rows bit-identical (0/2,560 values differ). This supports
the arithmetic mirror as a fix for this operator row, not as an end-to-end
migration qualification.

The accepted-prefix service GDN hashes first differ at endpoint 511, ordinal 4;
the first generated-token mismatch is at position 517 (initial ID 819, recovery
ID 264). Both supervised runs passed with minimum host/admission availability
of 14.22 GiB for delayed control and 14.33 GiB for adaptive. Across 164 and 161
memory samples, cgroup `high`, `max`, `oom`, and `oom_kill` counters remained
zero. Clocks were observed but not controlled, and energy was not attributed
to requests.

The later [layer-4 Q8_1 mirror follow-up](../adaptive-layer1-3-4-combined-mirror-prompt-tail505-511-pair/README.md)
removes this selected layer-4 row difference in a new randomized service pair.
That follow-up finds the next activation difference beyond the captured
layer-5 transition, so this report localizes one adaptive boundary but does not
explain all persistent-state drift. Phase 5 remains open.

Reproduce the pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261056 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 4 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 4 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 4 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 4 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-layer4-prompt-tail505-511-pair
```

Raw captures, per-position oracle activation and outputs, comparisons, service
logs, memory samples, and supervisor records are retained with this report.

# Layer-9 expert-235 migration at prompt position 505 — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M model at revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran the same short/long/recovery request sequence (512, 2,048, 512 input
tokens; 12 generated tokens requested). Arm order was delayed control then
adaptive. The adaptive arm used opt-in Q8_1 mirrors at layers 1, 3, 4, 6, and
8, each scoped to its measured expert weight pair.

At model layer 9, positions 506–511 have identical MoE routes, expert rows,
and combined output across adaptive initial/recovery. Position 505 is the one
changed row: expert 235 moves CPU-to-GPU with identical input, route IDs, and
router weights, and its row and combined output differ. The layer-9 GDN
intermediate first differs in `ffn_y` at position 505. Layer-9 pre/post GDN
state at endpoint 511 and committed state at positions 506, 508, 510, and 511
are bit-identical across adaptive initial/recovery. Delayed control is exact.

The independent `native_expert_parity` oracle identifies expert 235 as
IQ2_S/IQ4_NL, matching both service owner rows exactly at position 505. Default
CPU/GPU output differs in all 2,560 values (relative L2 `0.01401`). With
`STRATA_NATIVE_CPU_Q8_1_DOT=iq2_s/iq4_nl@layer=9`, CPU and GPU outputs are
bit-identical for this captured input (0/2,560 differing).

With this arm configuration, adaptive recovery returns all 12 token IDs that
match its initial request, but terminal `gdn`, `tail`, `pooled`, `pooled_full`,
and `kv` fingerprints still differ. The first service GDN hash difference is
ordinal 8 at accepted endpoint 511. Delayed control has no token or recorded
GDN-hash differences. Both supervised runs passed; minimum host/admission
availability was 14.14 GiB for delayed control and 14.26 GiB for adaptive.
Across 163 and 160 memory samples, cgroup `high`, `max`, `oom`, and `oom_kill`
counters were zero. Clocks were observed but not controlled; energy was not
attributed to requests.

The layer-9 Q8_1 mirror is tested in a fresh pair with captures at layer 10,
where the accepted-prefix GDN hashes first diverge. This is correctness
localization for one model and workload, not a performance result or full
persistent-state qualification. Phase 5 remains open.

Reproduce the pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261063 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 9 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 9 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 9 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 9 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-combined-mirror-layer9-prompt-tail505-511-pair
```

Raw captures, oracle outputs, comparisons, service logs, memory samples, and
supervisor results are retained here.

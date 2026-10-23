# Layer-11 QSA/MoE rows and layer-12 state — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M model
from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran short/long/recovery requests with 512, 2,048, and 512 prompt tokens,
and a 12-token generation limit. Arm order was delayed control then adaptive.
The adaptive arm used exact-pair Q8_1 CPU mirror rules at layers 1, 3, 4, 6,
8, 9, and 10.

At QSA/MoE layer 11, the verifier routes, expert IDs, and router weights match
across adaptive initial/recovery. Expert 179 changes CPU-to-GPU at positions
506–511; expert 201 changes at positions 505 and 507. Their changed rows and
combined MoE output differ. No other expert row is reported as changed in this
capture. Independent same-input `native_expert_parity` oracles match the
service CPU/GPU rows for expert 179 at position 511 and expert 201 at position
505. Both are IQ2_S/IQ4_NL; the exact layer-11 Q8_1 mirror makes each CPU/GPU
oracle pair bit-identical (0/2,560 differing values).

At GDN layer 12, the first captured intermediate difference is input `x` at
all positions 505–511. The raw recurrent and convolution state at position
511 differs across adaptive initial/recovery before and after the selected row;
the raw commit at position 511 matches both corresponding service GDN hashes.
The delayed-control arm remains exact. The adaptive requests have no shared
12-token response prefix: all 12 recovery token IDs differ, with first IDs 760
and 27775. The service-hash comparator therefore records the first token
mismatch at accepted endpoint 511 and emits no post-mismatch hash comparisons.
Adaptive terminal fingerprints differ in `gdn`, `ple`, `tail`, `pooled`,
`pooled_full`, `kv`, and `ple_prev`.

Both supervised runs passed; minimum host/admission availability was 14.22
GiB for delayed control and 14.18 GiB for adaptive. Across 163 and 163 memory
samples, cgroup `high`, `max`, `oom`, and `oom_kill` counters were zero. Clocks
were observed but not controlled, and energy was not attributed to requests.
The direct expert oracles support the owner-dependent QSA/MoE rows, but the
layer-11 mirror and a fresh layer-12 trace are still needed to test whether
those rows explain the following GDN state difference. This is correctness
localization for one model and workload, not a performance result or a complete
state-transaction result. Phase 5 remains open.

An extra position-511 probe for expert 201 is retained separately. Expert 201
is not routed at that position, and the service-row comparator rejects it; it
is not included in the oracle conclusions above.

Reproduce the pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261065 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 11 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 12 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 12 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 12 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-combined-mirror-layer11-12-prompt-tail505-511-pair
```

Raw captures, oracle outputs, comparisons, service logs, memory samples, and
supervisor results are retained here.

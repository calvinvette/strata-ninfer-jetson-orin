# Layer-8 expert-196 owner change — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M model at revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran the same 512-token short, 2,048-token long, and recovery requests with
a 12-token generation limit. Arm order was delayed control then adaptive. The
adaptive arm used the opt-in Q8_1 CPU mirrors for IQ2_S/Q2_0 at layer 1 and
IQ2_S/IQ4_NL at layers 3, 4, and 6.

At model layer 8, the captured dispatch inputs, expert IDs, and router weights
match across adaptive initial and recovery requests. Expert 196 changes
CPU-to-GPU ownership at positions 506, 507, 509, 510, and 511. Its row and the
combined MoE output differ at those positions; positions 505 and 508 are exact.
Layer-8 GDN intermediates first differ at `ffn_y` for those same five positions.
The layer-8 recurrent and convolution state at position 511 and committed
states at positions 506, 508, 510, and 511 are bit-identical across adaptive
initial/recovery. The raw committed state at 511 matches service GDN ordinal 6
for both records. Delayed-control routes, outputs, committed state, and service
GDN hashes remain exact.

An independent same-input `native_expert_parity` oracle confirms expert 196 is
IQ2_S/Q2_0 and matches the service's CPU and GPU rows exactly at position 511.
Default CPU/GPU output differs in all 2,560 values (relative L2 `0.01293`).
With the exact `STRATA_NATIVE_CPU_Q8_1_DOT=iq2_s/q2_0@layer=8` selector, CPU and
GPU outputs are bit-identical (0/2,560 values differ). An earlier retained
probe used IQ2_S/IQ4_NL at layer 8; that selector did not match this expert's
weight pair and is not evidence about the mirror's effect.

The first changed dispatch activation is at model layer 9 for positions
506–511, and layer 10 for position 505. The first adaptive service GDN hash
difference is ordinal 7 at endpoint 511. Adaptive recovery first differs from
the initial tokens at position 517 (initial ID 264, recovery ID 819); terminal
fingerprints differ in `gdn`, `ple`, `tail`, `pooled`, `pooled_full`, `kv`, and
`ple_prev`. Both runs passed supervision. Minimum host/admission availability
was 14.21 GiB for delayed control and 14.29 GiB for adaptive. Across 162 and
160 memory samples, cgroup `high`, `max`, `oom`, and `oom_kill` counters were
zero. Clocks were observed but not controlled; energy was not attributed to
requests.

The layer-9 paired capture with the exact layer-8 mirror is the next
localization step. This is correctness evidence for one model and workload, not
a performance result or full migration qualification. Phase 5 remains open.

Reproduce the pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261062 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 8 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 8 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 8 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 8 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-combined-mirror-layer8-prompt-tail505-511-pair
```

Raw captures, oracle outputs, comparisons, service logs, memory samples, and
supervisor records are retained with this report.

# Layer-10 expert-113/232 owner changes — Orin — 2026-10-20

This randomized adaptive/delayed-control pair used the pinned Coder IQ1_M GGUF
from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran 512-token short, 2,048-token long, and 512-token recovery requests,
with 12 generated tokens requested. Arm order was adaptive then delayed
control. The adaptive arm had Q8_1 CPU mirrors at layers 1, 3, 4, 6, 8, and 9.

At layer 10, expert 113 moves CPU-to-GPU at positions 505–509 and 511; expert
232 also changes owner at position 505. At each selected change, dispatch
activations, expert IDs, and router weights match, while the changed expert
row and combined MoE output differ. Position 510 is exact. The layer-10 GDN
intermediate first differs in `ffn_y` wherever those rows change. Layer-10
pre/post recurrent and convolution state at position 511 and commits at
positions 506, 508, 510, and 511 are bitwise identical across adaptive
initial/recovery. Delayed control is exact across its captured and service
state records.

Independent same-input `native_expert_parity` oracles at positions 505 and 511
identify both experts as IQ2_S/Q2_0 and reproduce the service CPU and GPU rows
exactly. Their default CPU/GPU relative-L2 differences range from `0.01229` to
`0.01391`. With the exact
`STRATA_NATIVE_CPU_Q8_1_DOT=iq2_s/q2_0@layer=10` selector, the CPU/GPU oracle
outputs are bit-identical for experts 113 and 232 at all three checked
expert-position inputs (0/2,560 differing values).

The first changed dispatch activation is at model layer 11. Adaptive recovery
still differs in six of 12 token IDs, first at position 517 (initial ID 819,
recovery ID 264); the first accepted-prefix service GDN hash difference is
ordinal 9, mapped to model layer 12. Adaptive terminal fingerprints differ in
`gdn`, `ple`, `tail`, `pooled`, `pooled_full`, `kv`, and `ple_prev`. Both runs
passed supervision; minimum host/admission availability was 14.18 GiB for
adaptive and 14.34 GiB for delayed control. Across 163 and 161 memory samples,
cgroup `high`, `max`, `oom`, and `oom_kill` counters were zero. Clocks were
observed but not controlled, and energy was not attributed to requests.

The follow-up pair adds the layer-10 mirror and captures layer-11 MoE plus
layer-12 GDN/state. This is correctness localization for one model and
workload, not a performance result or completed migration qualification.
Phase 5 remains open.

Reproduce this pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261064 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 10 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 10 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 10 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 10 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-combined-mirror-layer10-prompt-tail505-511-pair
```

Raw captures, oracle outputs, comparisons, service logs, memory samples, and
supervisor results are retained here.

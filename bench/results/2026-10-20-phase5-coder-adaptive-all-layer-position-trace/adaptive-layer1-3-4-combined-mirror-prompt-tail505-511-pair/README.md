# Layer-4 Q8_1 mirror follow-up over the prompt tail — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M model at revision
`5348543e0147355ac9cbcb031184a3546350988e`, with candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran the same 512-token short, 2,048-token long, and short recovery requests
with a 12-token generation limit. Arm order was delayed control then adaptive.
The adaptive arm enabled the opt-in CUDA-order Q8_1 CPU mirror for
`iq2_s/q2_0@layer=1`, `iq2_s/iq4_nl@layer=3`, and `iq2_s/iq4_nl@layer=4`.

The preceding layer-4 trace found expert 153 moving CPU-to-GPU at positions
505, 508, and 509 with identical routes, weights, and inputs. Same-input
`native_expert_parity` runs at each position reproduced the service CPU and GPU
rows exactly. At position 505 the default CPU/GPU rows differed in all 2,560
values (relative L2 `0.01553`); enabling the layer-4 Q8_1 mirror made the oracle
CPU and GPU rows bit-identical (0/2,560 differing). Positions 508 and 509 also
matched their respective service rows exactly under the unmirrored oracle, with
relative CPU/GPU L2 differences `0.01430` and `0.01670`.

With all three mirrors enabled, layer-5 routes, router weights, per-expert rows,
and combined MoE output matched across adaptive initial and recovery requests
at positions 505–511. Captured layer-5 GDN intermediates, pre/post verifier
state at 511, and committed state at 506, 508, 510, and 511 also matched
bitwise. The raw committed state at position 511 matched service GDN ordinal 4
hashes for both requests. This localizes the next observed difference beyond
the captured layer-5 transition: dispatch activation first differs at model
layer 7 for positions 506–511 and at model layer 10 for position 505. The first
service GDN hash difference is ordinal 6 at accepted endpoint 511. The first
recovery token mismatch is at position 517 (initial ID 264, recovery ID 819).
This is a narrowed boundary, not a complete explanation of adaptive state drift.

Delayed control remained exact across its repeated short requests and all
recorded service GDN hashes. The adaptive arm had six differing recovery token
IDs and changed terminal fingerprints (`gdn`, `ple`, `tail`, `pooled`,
`pooled_full`, `kv`, and `ple_prev`). Both supervised runs passed; minimum
host/admission availability was 14.22 GiB for delayed control and 14.36 GiB for
adaptive. Across 207 and 159 memory samples respectively, cgroup `high`,
`max`, `oom`, and `oom_kill` counters remained zero. Clocks were observed but
not controlled; energy was not request-attributed.

Reproduce the paired service run from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261057 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 5 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 5 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 5 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 5 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-combined-mirror-prompt-tail505-511-pair
```

Raw captures, oracle outputs, comparisons, service logs, memory samples, and
supervisor results are retained here. The mirror remains opt-in. This is
correctness localization for one model and workload, not performance or
long-chain migration qualification; Phase 5 remains open.

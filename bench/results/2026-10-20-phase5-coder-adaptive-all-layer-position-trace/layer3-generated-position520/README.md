# Generated position-520 layer-3 operator trace — Orin — 2026-10-20

This supervised randomized pair used the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M snapshot at revision
`5348543e0147355ac9cbcb031184a3546350988e`, binary
`9212d8140eaac1c1544b426dcd60b95a921235d04633ab36735a7b209d804743`, and
`STRATA_NATIVE_CPU_Q8_1_DOT=all`. Both delayed-control and cap-8 adaptive arms
completed the short/long/short sequence and returned identical recovery token
IDs to their own initial short request. The experiment is a correctness
localization result, not a performance or quality comparison.

At absolute generated position 520, initial and recovery inputs to layer 3,
expert IDs, and router weights are bit-identical. In adaptive recovery,
expert 182 changes from CPU owner `-1` to GPU owner `0`. It is the only routed
expert output that differs at layer 3: 2,560/2,560 values change, with relative
L2 0.002819. The combined layer-3 MoE output changes in all 2,560 values
(relative L2 0.000245); the shared-expert result is identical. Layer 4 is the
first layer whose captured input activation changes. The delayed control has
no owner or activation differences and exact layer-3 expert and combined
outputs. At layer 26, adaptive GDN input `x` is already different, while the
delayed GDN fields remain bit-identical.

An independent same-input `native_expert_parity` run confirms the service
capture: the initial CPU-owned expert row matches the parity tool's CPU output
bit-for-bit, and recovery's GPU-owned row matches its GPU output bit-for-bit.
Expert 182 uses the IQ2_S/IQ4_NL pair. With the opt-in Q8_1 mirror, the parity
tool reports CPU/GPU relative L2 0.002819, improving on the default CPU path's
0.0182 but leaving a real difference. The tool also compares the hidden Q8_1
activation after SwiGLU: all 60 blocks differ (39 scale bytes, 63 stored-sum
bytes and 45 quantized-code bytes). Applying the CPU IQ4_NL down dot to the
GPU-produced hidden Q8_1 activation matches the grouped CUDA output exactly.
This narrows the remaining difference to gate/up or SwiGLU and hidden
quantization, before the down projection. The opt-in mirror is not a fix for
this observed route transition.

The initial and recovery final state fingerprints still differ in `gdn`,
`tail`, `pooled`, `pooled_full`, and `kv` for adaptive; delayed fingerprints
match. Minimum host/admission availability was 14.22 GiB for adaptive and
14.37 GiB for delayed, with zero sampled cgroup memory events. Neither arm
changed clocks, and energy was not measured.

`layer25-owner-comparison.json` contains all-layer route/input comparisons.
`adaptive-layer3-verifier-comparison.json` and
`delayed-layer3-verifier-comparison.json` compare same-service routed expert
parts, shared output and combined MoE output. The independent exact-row join is
`operator-checks/expert182-q8_1-mirror/service-parity-row-comparison.json`;
raw activations and CPU/GPU parity outputs are retained beside it. The first
Q8_1-input quantizer diagnostic is retained as a failed checker cell. Its host
oracle used round-away-from-zero for Orin's GGML NEON path, which uses
ties-to-even; it also modeled CUDA division without the build's fast-math
rounding. The corrected check passes: CPU codes and both stored-sum formulas
match independently, and CUDA codes are exact or within one quantization step
(one block is one step). CPU/GPU stored-sum bytes differ in 75/80 blocks by
design: GGML stores `d*sum(q)` while this CUDA path stores `sum(input)`. See
`q8_1-quantizer-check-corrected.txt`; this check does not change the routed-row
or persistent-state findings.

Reproduce the supervised pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --continuations 0 --capture-moe-positions 520 \
  --capture-verify-moe-layer 3 --verify-moe-positions 520 \
  --capture-verify-gdn-layer 26 --verify-gdn-positions 520 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/reproduction-layer3
```

Run the independent expert check separately with:

```sh
STRATA_NATIVE_CPU_Q8_1_DOT=all \
  build/integration/candidate/native_expert_parity \
  ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert 182 \
  --activation-f32 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer3-generated-position520/operator-checks/expert182-q8_1-mirror/activation.f32 \
  --dump-f32-dir /tmp/expert182-parity 3
```

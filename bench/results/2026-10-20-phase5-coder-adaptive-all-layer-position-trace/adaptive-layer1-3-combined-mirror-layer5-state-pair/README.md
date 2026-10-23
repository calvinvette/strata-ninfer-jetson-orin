# Layer-5 verifier and committed-state capture — Orin — 2026-10-20

This randomized same-service pair retained the layer-1/layer-3 CPU Q8_1
mirrors and captured layer-5 MoE/GDN data and raw GDN state at positions 511
and 516. Both arms passed supervision on the pinned Coder IQ1_M model.

The delayed arm was exact. In adaptive recovery, the layer-5 GDN intermediate
first differs at `h` for both positions 511 and 516; `x` and `qkv` precede it
unchanged in that capture order. The raw verifier pre-state at 511 already
differs in 786,409/786,432 recurrent values and 20,480/30,720 convolution
values. Its committed state differs in 786,405 recurrent values and
10,240 convolution values. The raw committed capture matches the service hash
at endpoint 511. The adaptive initial/recovery tokens first split at position
517. These records locate the state difference by layer and boundary but do
not identify its upstream cause.

Minimum host/admission availability was 14.20 GiB for both arms, with no
sampled cgroup pressure/OOM events. This is correctness evidence only.
Reproduce with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261052 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3' \
  --capture-moe-positions 516 \
  --capture-verify-moe-layer 5 --verify-moe-positions 516 \
  --capture-verify-gdn-layer 5 --verify-gdn-positions 516 \
  --capture-verify-gdn-state-layer 5 --gdn-state-positions 511,516 \
  --capture-gdn-commit-state-layer 5 --gdn-commit-state-positions 511,516 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-layer5-state-pair
```

Raw state, intermediate, request, service, campaign and supervisor records are
retained beside this report.

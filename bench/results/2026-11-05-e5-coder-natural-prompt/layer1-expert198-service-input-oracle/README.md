# Layer-1 expert input quantization boundary

Date: 2026-11-05. Coder IQ1_M, layer 1, prompt position 41, routed expert
198. This replays the two service-captured MoE inputs from the
[layer-boundary capture](../README.md#prompt-position-41-layer-boundary-capture).
It is a local numerical diagnosis, not a whole-request correctness or quality
qualification.

## Result

The Strata and strict-NInfer input rows differ in 2,320/2,560 FP32 values,
relative L2 `3.801687e-7`, maximum absolute delta `1.192093e-6`. Independent
Q8_1 quantization of each row changes only one of 80 blocks: block 76 has
identical integer codes but different stored FP16 scales (`0.0075340271` for
Strata and `0.0075302124` for NInfer). The pre-rounding scales differ by only
`4.66e-10`; the changed FP16 result is a rounding-boundary crossing.

The independent quantizer is checked against the actual CUDA quantizer for
both captures: `native_expert_parity --q8_1-quantizer` reports zero scale and
code mismatches and zero oracle errors for each row. The grouped expert replay
also reports bit-identical NInfer and native Strata outputs on each respective
same input (`changed=0`, `relative_l2=0` for expert 198). Thus the sampled
service delta is present in the activation before the expert projection, and
the fixed-input kernels agree. This demonstrates an input-Q8_1 scale boundary
for this row; attributing all observed layer-1 output or later recurrent-state
divergence to this one block would exceed the evidence.

Reproduce the independent block comparison from the repository root:

```sh
python tools/integration/compare_q8_1_flat_rows.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/layer1-expert198-service-input-oracle/strata-layer1-pos41-input.f32 \
  bench/results/2026-11-05-e5-coder-natural-prompt/layer1-expert198-service-input-oracle/ninfer-layer1-pos41-input.f32 \
  --width 2560
```

The resulting JSON is `q8-1-input-comparison.json`. Captured rows and raw
activations are evidence inputs; do not interpret the row-level diagnostic as a
performance measurement.

# Position-521 layer-39 expert-output trace — Orin — 2026-10-20

This supervised same-seed pair used the pinned Coder IQ1_M model, all eligible
layer-specific Q8_1 rules, prompt cache disabled, and candidate binary
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. It
captured all verifier MoE inputs, layer-39 routes/parts/outputs, and the
residual boundary at generated position 521. Both arms passed; minimum
host/admission availability was 14.18 GiB adaptive and 14.34 GiB delayed, with
zero cgroup pressure or OOM events.

Layer-39 verifier inputs, expert IDs and router weights match across the
adaptive initial and intermediate requests. Expert 90 (rank 6) moves from CPU
to GPU. It is the only changed expert contribution: 2,559/2,560 values differ
and all other nine expert rows match. The shared output is exact; the combined
MoE output differs in 2,556/2,560 values (relative L2 `2.10033e-5`). At the
following residual boundary, `after_layer_bo` changes while `after_layer_R`
and `after_layer_inj2` remain exact; the subsequent layer read changes `R`
and `xn`. Intermediate-to-recovery, recovery-to-continuation, and every
recorded delayed-control transition are bit-identical.

An independent same-input `native_expert_parity` replay confirms the service
activation is byte-identical to the oracle input (SHA256
`1f6a5307b1b0e57634f989881acae9f0c3a24f9e8f3fc3eae338becac2439adb`). The
captured initial CPU expert-90 output matches the independent CPU oracle
bit-for-bit; the intermediate GPU output matches the independent GPU oracle
bit-for-bit. Their Q8_1 outputs differ in 2,559/2,560 values (maximum absolute
delta `5.32605e-5`, relative L2 `1.20273e-4`). This directly joins the owner
transition to the changed service contribution.

Stage isolation narrows the numerical seam: Q8_1 inputs and all gate/up dot
outputs match; CPU and CUDA hidden Q8_1 blocks differ in only three of 60 FP16
`d` scales, with sums and integer codes exact. Running the CPU down projection
on the CUDA hidden blocks matches the grouped CUDA output in all 7,680 values.
Thus the remaining discrepancy is in the SwiGLU/hidden-scale calculation, not
gate/up dot or down projection. It propagates through expert 90's output,
layer-39's combined output, and the residual boundary. This explains the
sampled adaptive state divergence, but does not yet repair it or qualify other
inputs. A [global division-expression trial](silu-order-trial.md) made this expert
exact but regressed the previously exact layer-31 expert-22 row; that trial was
rejected and its source change reverted. The current raw layer-41 state delta
measures `7.27893e-4` relative L2 after position 521 and `7.38754e-4` after
position 522 in this trace. These two positions do not bound longer chains.

Reproduce the route/parts/output comparison from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position521-layer39-moe-q8-pair/compare_moe_sequence.py \
  --run-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position521-layer39-moe-q8-pair \
  --layer 39 --position 521
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position521-layer39-moe-q8-pair/compare_boundary_sequence.py \
  --run-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-generated-position521-layer39-moe-q8-pair
```

Raw captures and supervisor telemetry are under `adaptive-cap8/` and
`delayed-control/`. Parsed results are in `layer39-moe-sequence-analysis.json`,
`expert90-q8_1-oracle-join.json`, and `boundary-sequence-analysis.json`. Oracle
stage dumps and output are retained under `expert90-q8_1-oracle/` and
`expert90-q8_1-stage/`.

# Position-521 layer-40 verifier MoE capture — Orin — 2026-10-20

This supervised same-seed pair used the pinned Coder IQ1_M model, all eligible
layer-specific Q8_1 rules, prompt cache disabled, and candidate binary
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`. It
captured all verifier MoE inputs, layer-40 routes, expert parts and combined
outputs, plus the residual boundary at generated position 521. Both arms
passed. Minimum host/admission availability was 14.16 GiB adaptive and 14.32
GiB delayed; cgroup pressure and OOM counters stayed zero.

On the adaptive initial-to-intermediate transition, layer-40 expert IDs are
the same but router weights differ. All 25,600 captured expert-part values
(10 experts × 2,560 values) differ; the shared output differs in all 2,560
values and the combined output differs in 2,559. All eight layer-40 residual
boundary fields also differ. The verifier input capture identifies layer 40
as the first changed MoE input at this position, so this records the changed
layer-40 output after an already changed input; it does not establish that
layer 40 is the original source. Intermediate-to-recovery and
recovery-to-continuation are exact for routes, weights, parts, outputs and
boundary fields. Delayed control is exact across all transitions.

The next capture moves upstream to layer 39's verifier output and residual
boundary at position 521. This is a correctness localization, not a migration
fix or performance result.

Raw records and supervisor telemetry are retained in `adaptive-cap8/` and
`delayed-control/`. Parsed route/part/output comparisons are in
`layer40-moe-sequence-analysis.json`; verifier inputs are in
`verifier-input-analysis.json`; residual fields are in
`boundary-sequence-analysis.json`.

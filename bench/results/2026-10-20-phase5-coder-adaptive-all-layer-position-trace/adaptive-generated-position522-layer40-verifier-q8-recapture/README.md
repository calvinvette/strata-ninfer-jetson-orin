# Position-522 layer-40 verifier capture — Orin — 2026-10-20

This supervised same-service pair repeated seed 20261127 with all eligible
layer-specific Q8_1 CPU rules, prompt cache disabled, the Coder IQ1_M model at
revision `5348543e0147355ac9cbcb031184a3546350988e`, and the current candidate
binary (`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`).
It captured all verifier MoE inputs at generated position 522, layer-40 verifier
routes/parts/output, and raw layer-14 GDN state. Both arms passed; adaptive
minimum host/admission availability was 14.13 GiB, with no cgroup memory events.

In the adaptive arm, the first verifier MoE input difference remains layer 41
(7 later layers differ) on initial-to-intermediate; the intermediate-to-recovery
and recovery-to-continuation comparisons are exact. Delayed control remains
exact at all 48 captured layer inputs. At layer 40, verifier routes, IDs, router
weights, all per-expert parts, and the combined MoE output were bit-identical
across every request transition in both arms. Raw layer-14 GDN pre/post state
was also exact across requests. QSA hashes at ordinals 10 and 11 (model layers
43 and 47) differ on the first adaptive transition.

The matching layer-40 oracle for the two same-input owner-switch experts,
92 and 164, found default CPU/GPU relative-L2 differences of 0.773% and 1.456%;
the layer-specific Q8_1 outputs were bit-identical. Their captured combined
verifier output is also exact across requests, so the layer-40 MoE operator is
cleared for this position. The remaining boundary is after layer 40 and before
the layer-41 verifier input; the next capture will inspect residual and
hyperconnection fields there. No performance claim is made.

The paired traces and analyses are in `adaptive-cap8/`, `delayed-control/`,
`verifier-input-analysis.json`, `qsa-state-analysis.json`,
`selected-position-analysis.json`, and `layer40-verifier-parts-analysis.json`.
The direct operator result is `../adaptive-generated-positions521-522-layer39-q8-all-others-seed20261127/layer40-position522-owner-oracle.json`.

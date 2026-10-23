# Matched-seed layer-39 selector contrast — Orin — 2026-10-20

This supervised sequential pair repeats seed 20261127 from the all-layer-Q8_1
control, with the same model, binary, request sequence, prompt-cache setting,
12-token output cap, and continuation. The only selector change leaves layer 39
on its default CPU arithmetic; all other eligible expert format/layer pairs keep
the exact same Q8_1 rules. The pinned model is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. Candidate binary SHA256 is
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`.

Both arms passed supervision and all four requests per arm produced the same
12 token IDs. Minimum host/admission availability was 14.17 GiB for adaptive
and 14.20 GiB for delayed control; no cgroup memory events occurred. The raw
launch, per-arm telemetry and complete traces are retained in this directory.

The all-layer-Q8_1 reference first differed within the adaptive request history
at verifier input layer 40 for position 521 and layer 41 for position 522 on
initial-to-intermediate; intermediate-to-recovery was exact at both positions.
With only layer 39 returned to default CPU arithmetic, the adaptive input first
differed at layer 40 for both positions on both transitions. The delayed
control remained bit-identical at all captured layers and positions in both
configurations. QSA hashes at ordinals 10 and 11 (model layers 43 and 47) were
exact across the all-layer-Q8_1 intermediate-to-recovery transition, but
changed across that transition when layer 39 used default CPU arithmetic. The
same two QSA hashes changed on initial-to-intermediate in both configurations.
Raw layer-14 GDN pre/post state remained bit-identical across all four requests
at positions 521 and 522 in both configurations.

A direct cross-configuration comparison confirms the layer-39 selector changes
verifier tensors at layers 40–47, as expected from changing an upstream expert
operator. The matched-seed evidence therefore supports a narrow conclusion:
the tested layer-39 Q8_1 mirror preserves the sampled QSA recovery hashes for
this request history, while it does not remove the initial adaptive mismatch.
This is one correctness cell, not proof of a general cause, quality benefit,
or performance gain. The initial layer-40/41 divergence and the underlying
operator/state path still require investigation.

Reproduce the trace comparisons with:

```sh
python3 ../adaptive-generated-positions512-521-522-layer14-state/compare_verifier_inputs.py --run-dir .
python3 ../adaptive-generated-positions512-521-522-layer14-state/compare_qsa_layers.py --run-dir .
python3 ../compare_selected_positions.py --run . --output selected-position-analysis.json
```

The cross-configuration per-tensor and raw-state comparison is saved in
`same-seed-selector-contrast.json`.

## Earlier owner-switch oracle screen

The same-input oracle screen in `screen_prior_owner_oracles.py` examined all 16
unique owner-switch rows below layer 39 whose verifier inputs, routes and expert
IDs matched between the adaptive initial/intermediate requests. These included
23 position/expert samples at positions 521 and 522. Default CPU/GPU output
relative L2 ranged from 1.06% to 1.56%; setting the corresponding layer-specific
Q8_1 rule made every sampled row bit-identical. This clears those isolated
expert operators under the tested inputs and arithmetic contract. It does not
by itself establish the service's combined MoE output or recurrence state for
each row. The layer-39 expert-90 position-521 Q8_1 residual remains a separate
small delta, and layer 40 is under direct verifier capture.

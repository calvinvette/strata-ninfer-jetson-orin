# Layer-8 weighted CPU-output delta reconstruction — Orin — 2026-10-19

This repeated two-arm run captures the verifier's device-side top-10 expert IDs
and float32 router weights at layer 8, alongside the exact device `ffn_x` and
combined `ffn_y`, plus CPU-owned expert rows. It compares the opt-in CPU Q8_1
mirror with the default CPU arithmetic used by the layer-1 GPU-placement arm.
The model is the pinned Coder IQ1_M artifact; both services used the same
512-token prompt, 16 generated positions, MTP2, FP16 KV, 3,000-slot profile,
no adaptive swaps and prompt cache off. Arm order was randomized by seed
20261019. Each service ran in its own 28-GiB cgroup scope, with dynamic clocks
observed and no clock controls.

At position 511/token 271, both arms have bitwise-identical device `ffn_x`,
top-k IDs, router weights and owner vectors. The seven CPU-owned output rows
all differ in 2,560/2,560 values (per-expert relative L1 1.189%–1.505%). The
weighted sum of those seven CPU output deltas reconstructs the measured
combined device `ffn_y` delta across all 2,560 values with maximum absolute
residual `5.63e-9` and relative-L1 residual `2.266e-5` (0.00227% of the
combined delta). Remaining float32 accumulation and fused-operation rounding
accounts for the small residual. This directly links the layer-8 CPU arithmetic
difference to the combined output difference for this one matched row. It does
not establish downstream state or answer-quality impact, and no performance
claim is made.

Both arms passed supervision. Minimum host/admission availability was
14.39/14.39 GiB for the Q8_1 mirror and 14.41/14.41 GiB for default CPU;
maximum observed cgroup high, max, OOM and OOM-kill counters were all zero.
Exact prompt, completion, model, source and binary identities are recorded in
`artifact-identity.json`; raw route weights, outputs, device captures and
supervisor telemetry are retained per arm.

Reproduce from the repository root on Orin with:

```sh
bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_layer8_weighted_pair.sh
```

Recompute the weighted comparison with:

```sh
python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_layer8_weighted_delta.py
```

The opt-in device route capture uses `STRATA_VERIFY_DUMP_MOE_ROUTE_LAYER` and
`STRATA_VERIFY_DUMP_MOE_ROUTE_PATH`; without these environment variables it
allocates no route-diagnostic buffer and adds no capture copies. Phase 5
remains open because this is one decode row and does not resolve the persistent
state continuation difference or establish broad quality.

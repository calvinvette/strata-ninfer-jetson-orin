# Layer-25 shared and combined output capture — Orin — 2026-10-20

This same-service follow-up extends the position-511 capture on model layer 25
with the shared-expert vector and the combined MoE vector before residual
application. It uses the pinned Coder IQ1_M artifact from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and the adaptive cap-8
512→2,048→512→continuation sequence. The candidate binary SHA256 is
`5040faeec4476f651df839e2a18484731a597b5e1f0bed4a74e726f32aa006ac`.

At position 511, the initial and recovery verifier rows had the same token,
router IDs and weights, and all ten routed-expert rows. The 2,560-float
shared-expert outputs also matched bitwise. The 2,560-float combined MoE vectors
matched bitwise after weighted combine and before residual/hyper-connection
application. This moves the unresolved boundary downstream of the measured
layer-25 MoE path for this position. It does not identify whether the residual
write, following QSA state, or model layer 26 first introduces the difference.

The 28-GiB supervised run passed with 14.37 GiB minimum host/admission
availability, 10.92 GiB maximum scope use, and zero scope memory events. It took
182.8 seconds. Clocks remained dynamic; EMC readback was denied and energy was
not request-attributed. This is correctness localization, not performance
measurement.

The route, expert-parts, shared/combined-output captures, analysis, engine log,
and supervisor telemetry are retained in this directory. Reproduce from the
repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-output-followup/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --capture-verify-moe-layer 25 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-output-followup/run

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer25_verifier_parts.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-output-followup/run \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-output-followup/analysis.json
```

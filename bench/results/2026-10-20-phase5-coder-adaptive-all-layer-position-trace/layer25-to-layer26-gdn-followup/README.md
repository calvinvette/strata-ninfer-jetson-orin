# Layer-26 GDN intermediate trace — Orin — 2026-10-20

This same-service run captured selected layer-26 GDN intermediates at position
511 during the initial and recovery short requests, alongside the layer-25
router/expert/shared/combined captures. It uses the pinned Coder IQ1_M artifact
from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and the adaptive cap-8
512→2,048→512→continuation sequence. The candidate binary SHA256 is recorded
in `gdn-analysis.json`.

At layer 26, the captured input `x`, QKV projection, convolution output `h`,
gate, beta, and `z` matched bitwise across the two requests. The first
captured difference was the recurrent normalized output `y`: 5,152 of 6,144
values differed, with maximum absolute difference `2.7354e-4` and relative L2
`2.5005e-4`. The following GDN projection and feed-forward input also differed.
This localizes the position-511 mismatch to the state-dependent recurrence
output despite identical captured per-token inputs. The persistent GDN state
immediately before this token was not captured, so the run does not show when
or how that state diverged.

The 28-GiB supervisor passed with 14.36 GiB minimum host/admission
availability, 10.77 GiB maximum scope use, and zero scope memory events. It took
183.6 seconds. Clocks remained dynamic; EMC readback was denied and energy was
not request-attributed. This is correctness localization, not performance
measurement.

The GDN and MoE captures, analysis, service log, and supervisor telemetry are
retained in this directory. Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-to-layer26-gdn-followup/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --capture-verify-moe-layer 25 \
  --capture-verify-gdn-layer 26 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-to-layer26-gdn-followup/run

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer26_gdn_intermediates.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-to-layer26-gdn-followup/run \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-to-layer26-gdn-followup/gdn-analysis.json
```

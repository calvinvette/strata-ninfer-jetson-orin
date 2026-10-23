# Expert-11-first two-live layer-4 state capture

This is a one-run correctness diagnostic on Orin, using the current candidate
binary (`9ddadbf0…` SHA256), Coder IQ1_M, target-only batch mode, two concurrent
requests, a 1,500 MiB expert cache, 1,024-token context, and six generated
tokens. A static profile moved model layer 1 / expert 11 to the first residency
rank (profile SHA256
`8a590044b65ae494e3462067cd76878f3b71ca23519c182ac4660d88c6d9f114`). The
profile is diagnostic only; it is not a recommended serving configuration.

Both batch token streams matched their separate serial controls for all six
tokens. The capture recorded layer-4 routes/owner rows and all 36 committed GDN
states at generated position 68 and position 71. At position 71 the route rows
explicitly map prompt 0 to slot 0 and prompt 1 to slot 1. At position 68 the
prompt-1 route explicitly identifies slot 1, while prompt 0's row omits its
slot field; the analyzer maps that remaining row to slot 0 by complement and
checks the assignment against position 71. This missing slot field is a trace
format limitation.

For prompt 0 / slot 0, all 36 committed GDN states match serial at position 68.
At position 71, 31 of 36 layers differ; the first changed layer is model layer
6 (796,416/817,152 values, relative L2 `0.0008231`). The layer-4 activation,
expert IDs/weights and owner codes are exact at that position. All ten expert
parts, shared output and combined MoE output are bit-identical. This places the
selected row's observed downstream state change after an exact layer-4 MoE
result, but does not identify whether residual handling or later layers cause
it.

For prompt 1 / slot 1, state already differs at position 68: model layer 5 is
the first changed GDN layer (796,610/817,152 values, relative L2 `0.001193`).
At position 71, 33 of 36 layers differ, first at model layer 4 (817,141 values,
relative L2 `0.003735`). Layer-4 expert IDs match serial, but its input
activation differs in all 2,560 values (relative L2 `0.004587`) and router
weights differ. Its expert output therefore cannot be attributed to an owner
change using this pair.

The 28-GiB supervisor passed with 17.44 GiB minimum physical/admission
availability across 53 samples; sampled cgroup low/high/max/OOM/OOM-kill
counters were zero. Clocks were observed dynamically; EMC readback was denied;
energy was not measured. This is correctness localization, not performance or
quality evidence, and it does not qualify multi-live serving. The capture shows
that moving expert 11 earlier does not make both live rows state-exact. The
multi-live mismatch and its first responsible operation remain unresolved.

The compact result is `analysis.json`; `analyze_layer4_profile_capture.py`
checks route/slot joins, accepted-state record coverage, exact part/output
parity for the paired prompt-0 row, token identity and supervisor memory
events. Full arrays, JSONL dispatches, service logs and telemetry remain in the
local sibling `run-two-live-layer4-profile-e11-first-positions68-71/` and
`supervisor-two-live-layer4-profile-e11-first-positions68-71/` directories,
outside Git.

Recreate the temporary profile, capture and compact analysis from the
repository root on Orin:

```sh
python3 bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/make_expert11_first_profile.py \
  --output /tmp/layer4-expert11-first-profile.bin

python3 tools/integration/run_control.py \
  --output bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/supervisor-two-live-layer4-profile-e11-first-positions68-71 \
  --timeout 300 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/capture_two_live_layer4.py \
  --positions 68,71 --tokens 6 --moe-layer 4 --expert-cache-mib 1500 \
  --expert-profile /tmp/layer4-expert11-first-profile.bin \
  --output bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/run-two-live-layer4-profile-e11-first-positions68-71

python3 bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/analyze_layer4_profile_capture.py \
  --capture bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/run-two-live-layer4-profile-e11-first-positions68-71 \
  --profile /tmp/layer4-expert11-first-profile.bin \
  --supervisor bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/supervisor-two-live-layer4-profile-e11-first-positions68-71 \
  --output /tmp/layer4-profile-e11-analysis.json
```

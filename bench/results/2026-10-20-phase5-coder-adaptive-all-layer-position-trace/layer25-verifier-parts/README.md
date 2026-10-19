# Layer-25 verifier router and expert-parts capture — Orin — 2026-10-20

This same-service follow-up captures verifier routing and all ten expert output
rows at position 511 on model layer 25 during the initial and recovery short
requests. It uses the Coder IQ1_M artifact from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, with the adaptive cap-8 sequence
512→2,048→512→continuation. The candidate binary SHA256 is
`5f4859ca88b0967dd0447afd471778c7f014b368feb32f4825c0e557ee66cad8`.

At position 511, the initial and recovery rows had the same token (271), ten
expert IDs and router weights. All 25,600 FP32 values in the ten routed expert
contributions, after `moe_hit_add` and before weighted combine, were bitwise
identical (0 differing values; max absolute and relative L2 differences were
zero). This rules out the captured router and routed expert contributions as
the source of the later layer-26 divergence for this row. The shared-expert
output, weighted combine, and residual write remain unmeasured, so the cause
is unresolved.

The supervised run passed with `MemoryMax=28G`, minimum host/admission
availability 14.31 GiB, maximum scope use 10.85 GiB, and zero scope
low/high/max/OOM/OOM-kill events. It took 184.9 seconds. Clocks remained
dynamic; EMC readback was denied and energy was not request-attributed. These
are diagnostic correctness measurements, not a performance comparison.

The raw route and expert-parts captures, comparison JSON, service log, and
supervisor telemetry are retained in this directory. Reproduce from the
repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-parts/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --capture-verify-moe-layer 25 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-parts/run

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer25_verifier_parts.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-parts/run \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer25-verifier-parts/analysis.json
```

The opt-in capture uses the normal verifier graph path and applies the position
filter when writing the completed graph result. This matters because verifier
graphs are captured once and replayed for later token positions. The diagnostic
is disabled unless both layer and output path are explicitly set.

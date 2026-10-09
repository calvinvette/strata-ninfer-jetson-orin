# Integration experiment specifications

[`campaign.json`](campaign.json) declares staged factor grids. It deliberately
contains abstract, capability-gated candidate settings rather than executable
engine flags. Generate the proposed cells and paired order with:

```sh
python3 tools/integration/plan_matrix.py --output /tmp/strata-ninfer-matrix.json
python3 tools/integration/plan_matrix.py --suite mtp_kv_workload --confirmation \
  --output /tmp/strata-ninfer-confirmation.json
```

All generated rows are `not_run`; resource/capability admission remains
`unverified`. The original campaign and randomization seed are embedded. Pair
baseline/candidate within the same day, artifact and thermal block; the output
order randomizes each pair. The capacity ladder stays ascending and requires
recovery at each point. Never execute all proposed rows without admission.

Baseline/candidate means revision for an identical factor cell. If a candidate
factor has no equivalent baseline capability, record it as unsupported and use a
separately declared ablation against its qualified control, not a false paired
speedup. Kernel cells require actual shape/format bindings and compiled resource
checks before numerical qualification. Cache fractions refer to each matched
control's safe automatic cap; record bytes and keep the absolute budget fixed
when isolating a code change.

Use [BENCHMARKS.md](../../docs/integration/BENCHMARKS.md) for metrics, numerical and
memory constraints, replication, interactions, promotion rules and graph outputs.
[`result.schema.json`](result.schema.json) defines the future per-repetition
interchange record; no integration result records exist yet. The execution/result
adapter and result-schema validation are Phase 1 work. Do not relabel legacy JSON
as this schema without explicit field/unit conversion.

# Excluded Coder CPU-order recovery attempt — Orin — 2026-10-16

This exploratory Phase 5 run is excluded from numerical and quality
conclusions. It repeated the accepted-only short→long→short Coder sequence with
`--expert-cache-cpu-order`, but source inspection found that the flag dispatches
to `moe_hit_grouped_s2_cpu_order`, which is written for the packed Q2_0 expert
layout. The Coder pack is native, with per-layer GGUF formats such as
IQ3_XXS/IQ4_NL. The service accepted this incompatible combination, so the run
cannot establish whether CPU-order arithmetic affects Coder recovery drift.

Two fresh services each processed the same 512-token short prompt, the same
2,048-token swap-inducing prompt and the short prompt again, generating 16
tokens per request with accepted-only adaptation every four tokens. Both
independent services produced identical token IDs and all nine logged state
fields request-by-request. Within each service, recovery differed from the
initial short request at 14 of 16 token IDs. Seven logged fingerprints changed
and the dead-state fingerprint matched. These observations are retained, but
are not interpreted as a mechanism result because the option was incompatible.

The captured layer-0 path retained the same route transition pattern as the
prior run: all first seven aligned initial/recovery rows had identical
activations and expert IDs, with 18 of 70 owner assignments changed. The next
15 aligned rows had different activations. Adaptive refill-byte verification
and device residency-table verification passed at every logged apply point,
but those checks do not validate arithmetic for the native Coder layout. A
follow-up direct call to the Q2_0 helper with raw Coder IQ3_XXS/IQ4_NL weights
produced non-finite output and is also excluded. The diagnostic misuse was
removed and did not change the service implementation.

The unsupported run's timing is not used as performance evidence.

The 28-GiB supervised run returned 0 after 405.2 seconds. Across 384 memory
samples, minimum host availability was 14.26 GiB and minimum admission
availability was 9.36 GiB. Sampled cgroup `high`, `max`, `oom` and `oom_kill`
counters were zero. CPU clocks ranged 729.6–2,201.6 MHz and GPU clocks
306–1,300.5 MHz; clocks were observed dynamically, not controlled. EMC
readback was denied and energy was not request-attributed.

The artifact is the `IQ1_M` variant from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. Model and pack identities match
the earlier [route-change capture](../2026-10-14-phase5-current-source-route-change-capture/README.md).
The current service binary SHA256 is
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`; the
expert profile SHA256 is `a514661124d5305effe9c1bcecff7dc069af398b2b19ff9d11628a2cad0a8915`.
The tokenized short and long prompt hashes are recorded in `run/results.json`.

The original attempt command is retained in `run/` and the supervisor record.
With the current source, the same native Coder config now exits with status 2
before serving; the exact message and current binary identity are in
`format-guard-smoke.txt`:

```sh
python3 - <<'PY'
import json, subprocess
config = json.load(open("bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/baseline-mtp0-config.json"))
command = [config["exe"], "--serve", *config["args"], "--expert-cache-cpu-order"]
result = subprocess.run(command, text=True, capture_output=True)
print(result.stderr, end="")
raise SystemExit(0 if result.returncode == 2 and "native GGUF expert formats are unsupported" in result.stderr else 1)
PY
```

The harness adds only `--expert-cache-cpu-order` to the established route
capture configuration. Raw outputs, state fingerprints, captured dispatches,
service logs, supervisor telemetry and hashes are retained for audit. The
result is an unsupported cell, not a negative mechanism test or Phase 5
closeout. The broader recovery cause, graph lifetime gates and quality impact
remain open.

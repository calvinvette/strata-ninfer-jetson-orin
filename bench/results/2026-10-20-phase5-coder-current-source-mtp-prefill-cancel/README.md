# Current-source Coder IQ1_M MTP4 early-prefill cancellation and recovery — Orin — 2026-10-20

This Phase 5 runtime check closed a streamed request during a 7,498-token
Coder IQ1_M prompt, then checked same-service recovery against a fresh-service
reference. It used the current candidate binary and shared-source hashes in
[`source-identity-sha256.txt`](source-identity-sha256.txt), the pinned model
revision and MTP runtime listed in [`artifact-sha256.txt`](artifact-sha256.txt),
FP16 KV, and the configured MTP4 accepted-only profile. Model and runtime
artifacts remained under `~/models/strata-orin-validation/`.

The client closed the stream one second after receiving HTTP headers. The
engine had read 64/7,498 prompt tokens and generated zero tokens; it logged
the request as canceled. The same service then returned exactly `Hello Orin!`.
All 11 persistent-state fingerprints after recovery matched those from a fresh
service given the same short request, including the main GDN/KV/PLE state and
MTP state. The fresh reference returned the same answer.

The 28-GiB supervisor passed in 51.2 seconds across 50 samples. Minimum host
and admission availability was 13.05 GiB, peak scope use was 13.34 GiB, and
`low`, `high`, `max`, `oom` and `oom_kill` counters were zero. CPU/GPU clocks
were observed dynamically; EMC readback was denied and energy was not
request-attributed. The full stream/recovery result, engine logs, server
configurations, and memory/clock telemetry are retained here.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/coder-mtp-prefill-cancel/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/cancel_long_prefill_recovery.py \
  --config bench/results/2026-10-20-phase5-coder-current-source-mtp-prefill-cancel/config.json \
  --long-workload bench/results/2026-10-20-phase5-coder-current-source-mtp-prefill-cancel/workload.json \
  --output /tmp/coder-mtp-prefill-cancel/run \
  --cancel-after-s 1 --compare-recovery-state
```

This adds one early-prefill cancellation point for this model, binary, profile
and prompt. It does not qualify every cancellation boundary, other KV formats
or prompts, and it does not resolve adaptive CPU/GPU migration state drift.
Phase 5 remains open.

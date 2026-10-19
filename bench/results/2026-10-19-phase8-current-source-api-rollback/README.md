# Pinned-control API rollback check — Orin — 2026-10-19

The pinned Strata control and the current integration candidate both passed
the same seven-case real-model API suite on the Coder IQ1_M artifact. The run
used one shared 8K configuration: the same pack, two GGUF shards, expert
profile, 3,000-slot expert cache, prefill chunk 128, MTP disabled, mmap
experts and prompt cache disabled. Only the executable and per-arm log/output
paths differed. The model remained under `~/models/strata-orin-validation/`.

Each arm passed three repeated greedy responses, OpenAI streaming, Anthropic
streaming, decode cancellation and prefill disconnect, with an exact
`Hello Orin!` recovery response after each cancellation. The pinned control
used binary SHA256
`edbc0a85fc706fd929f9ea5ad1041c3fed25a0cc107356bcc82e59c2431a5249` from
commit `0be090c`. The candidate used SHA256
`b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa`, built
from engine source commit `b6ea61888cb1ffb0bf92e79217d6a88d46178111`. Model
and binary identities are retained in `artifacts.json` and
`source-revisions.txt`.

Both arms ran in separate 28-GiB scopes. Minimum host/admission availability
was 14.18/14.18 GiB for control and 14.28/14.28 GiB for candidate. Across 35
and 37 samples, respectively, cgroup low/high/max/OOM/OOM-kill counters stayed
zero. Clock observations were read-only and dynamic; EMC readback was denied;
energy was not attributed. Both servers exited cleanly. The independent
per-arm protocol reviews and paired review are retained beside the raw
requests, engine/server logs and supervisor telemetry.

The initial harness attempt is retained under `supervisor-control/`; it stopped
before model startup because system Python lacked the `requests` package. The
successful retry used the existing model-pack virtual environment. That
environment issue is excluded from runtime results.

The suite's prefill-disconnect case closed the client stream after 0.50 seconds
but did not retain evidence that prompt ingestion had begun. This report does
not claim active-prefill cancellation; a separate current-profile test must
show prompt progress before disconnect for that gate.

Reproduce the successful runs from the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-19-phase8-current-source-api-rollback/supervisor-control-retry \
  --timeout 3600 --interval 1 --sample-clocks -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-17-phase7-q2-prefill128/run_protocol_cancel.py \
  --config bench/results/2026-10-19-phase8-current-source-api-rollback/control-config.json \
  --output bench/results/2026-10-19-phase8-current-source-api-rollback/control --port 18883

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-19-phase8-current-source-api-rollback/supervisor-candidate \
  --timeout 3600 --interval 1 --sample-clocks -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-17-phase7-q2-prefill128/run_protocol_cancel.py \
  --config bench/results/2026-10-19-phase8-current-source-api-rollback/candidate-config.json \
  --output bench/results/2026-10-19-phase8-current-source-api-rollback/candidate --port 18883

python3 bench/results/2026-10-19-phase8-current-source-api-rollback/verify.py
```

This establishes a model-backed API rollback and recovery path for this shared
configuration. It does not qualify the candidate-only Q2_0 release profile on
the pinned binary, active-prefill cancellation, API performance, or broad
quality. Phase 8 remains open.

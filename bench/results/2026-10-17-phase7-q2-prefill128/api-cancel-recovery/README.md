# Selected Q2_0 profile API protocol and disconnect checks — Orin — 2026-10-17

The selected Q2_0 MTP-off/prefill-128 profile passed all seven scenarios in
Strata's real-model API protocol suite: three repeated greedy responses, OpenAI
streaming, Anthropic streaming, decode cancellation and prefill-disconnect
handling. The two cancellation cases were each followed by an exact
`Hello Orin!` response from the same service process. The independent review
passes the seven scenario statuses and confirms that the engine logged
`cancel=True` for both disconnects.

The decode cancellation waited for visible streamed content before closing the
client stream; the engine logged cancellation and the subsequent same-service
request passed. The prefill-disconnect case closed the stream after 0.50 seconds
and also logged cancellation with same-service recovery. However, the retained
engine log does not show prompt-progress evidence for that short prefill case.
The active-prefill cancellation claim comes from the separate [progress-gated
long-prompt run](../api-prefill-cancel/README.md), which logged 256 of 7,498
prompt tokens before disconnect and then logged `cancel=True`.

The runtime config retained the selected profile flags: Q2_0, FP16 KV, no MTP,
8,192 context, 3,000 exact expert slots, prefill chunk 128, eight workers,
prompt cache disabled, adaptive swaps disabled and a 3,072-MiB workspace
reserve. The protocol runner added only the test port/log path and
`STRATA_INTEGRATION_TRACE=1`. The model, pack, tokenizer and profile remained
under `~/models/strata-orin-validation/`.

The test ran under a 28-GiB cgroup limit and the six-GiB physical-host guard.
Minimum host and effective admission availability were both 17.87 GiB; cgroup
`low`, `high`, `max`, `oom` and `oom_kill` counters stayed zero. The server
exited cleanly and port 18883 was no longer listening after the run. This is
one protocol/cancellation profile point, not persistent-state parity, broad
quality, stress capacity or a product guarantee.

The candidate binary SHA256 was
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built
from source commit `53d7c7a419f214b4133a2319bdcdf127f23ba1c4`. The checkout was
`d94c4dec72e12e0813903a36665e3fcac0f8b063`; engine/backend/CMake/test sources
are unchanged from the candidate build source. `artifacts.json` records the
model and profile identity. `SHA256SUMS.txt` covers the retained config,
protocol output, independent review and supervisor telemetry.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/strata-q2-prefill128-api-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-17-phase7-q2-prefill128/run_protocol_cancel.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/config.json \
  --output /tmp/strata-q2-prefill128-api-run --port 18883

python3 bench/results/2026-10-17-phase7-q2-prefill128/api-cancel-recovery/review_protocol.py \
  --result /tmp/strata-q2-prefill128-api-run/result.json \
  --output /tmp/strata-q2-prefill128-api-run/independent-review.json
```

The Python interpreter is the existing model-pack venv because it provides the
`requests` dependency used by the inherited protocol test. No environment or
model files were added to Git.

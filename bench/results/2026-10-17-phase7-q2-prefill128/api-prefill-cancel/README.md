# Q2_0 selected-profile active-prefill cancellation and recovery — Orin — 2026-10-17

The selected Q2_0 MTP-off/prefill-128 profile passed a progress-gated active
prefill cancellation and same-service recovery check. The configured context
was 8,192 tokens. The runner submitted the 7,498-token retrieval prompt and
waited for the engine to log `256 of 7,498 tokens` before closing the raw HTTP
client socket, 16.75 seconds after the request began. The engine then logged
`done: 0 tokens ... cancel=True`, confirming that the request was cancelled
before prefill completed. A short follow-up on the same service returned the
exact answer `Hello Orin!`. The independent reviewer verified incomplete prompt
progress before disconnect, the engine cancellation record, recovery and
service teardown; its overall result was pass.

The config retained Q2_0, FP16 KV, MTP off (`--spec 2`, no MTP model), 8,192
context, 3,000 expert-cache slots, prefill chunk 128, eight workers, disabled
prompt cache, disabled adaptive swaps and a 3,072-MiB workspace reserve. The
test added `STRATA_INTEGRATION_TRACE=1` for retained instrumentation. Model,
pack and tokenizer files remained under `~/models/strata-orin-validation/`.

The run was supervised with a 28-GiB cgroup limit and the six-GiB physical-host
guard. Minimum host and effective admission availability were 18.10 and 16.78
GiB; cgroup `low`, `high`, `max`, `oom` and `oom_kill` counters stayed at zero.
The service exited and port 18884 was no longer listening afterward. This is
one cancellation/recovery point for this profile, not persistent-state parity,
long-context quality or a general product guarantee.

Two earlier attempts are retained. The first watched the engine log instead of
the server progress log; it allowed the full retrieval request to finish and
then failed its progress timeout. The second used `requests.post(stream=True)`,
which waited for response headers until prefill completed; it was interrupted
through the runner cleanup path and is not counted as a result. The successful
third attempt uses a raw HTTP socket and closes only after an incomplete prompt
count appears in the server log. These failures and the passing retry are all
included in `SHA256SUMS.txt`.

The candidate binary SHA256 was
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built
from source commit `53d7c7a419f214b4133a2319bdcdf127f23ba1c4`. The checkout was
`d94c4dec72e12e0813903a36665e3fcac0f8b063`; engine/backend/CMake/test sources
are unchanged from the candidate build source. `artifacts.json` records model,
config and workload identity.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/strata-q2-prefill128-active-cancel-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-17-phase7-q2-prefill128/run_prefill_cancel.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/workload.json \
  --output /tmp/strata-q2-prefill128-active-cancel-run

/home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-17-phase7-q2-prefill128/review_prefill_cancel.py \
  --result /tmp/strata-q2-prefill128-active-cancel-run/result.json \
  --output /tmp/strata-q2-prefill128-active-cancel-run/independent-review.json
```

The model-pack venv supplies the `requests` dependency for health and recovery
calls; the cancellation request itself uses a raw HTTP socket so the client can
close while the server is still processing prompt tokens. The retry folders
retain raw memory, clock, service and `tegrastats` output.

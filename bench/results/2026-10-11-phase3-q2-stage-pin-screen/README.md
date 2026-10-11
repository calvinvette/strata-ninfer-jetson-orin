# Q2_0 pageable versus pinned expert staging screen — Orin — 2026-10-11

This three-pair same-day screen checks whether the existing pageable/pinned
expert-stage paths preserve output and persistent state on the Q2_0 cohort.
Each independent process used the 512-token formatted prompt, 64 generated
tokens, Q2_0 native model and PLE artifacts, 256 requested cache slots, 8K
context, prefill chunk 512, spec2 and the same prompt/cache/prefetch controls.
Only `STRATA_STAGE_PIN` changed between arms. Pair order was pinned/pageable,
pageable/pinned, pinned/pageable. The measurement used the integration
harness's trace-enabled correctness mode; timing is exploratory.

All six requests completed. Each pair matched generated token IDs, all nine
persistent-state fields and cache/prefetch counters. The harness observed the
expected `expert-stage-pageable-host` or `expert-stage-pinned-host` owner in its
respective arm. Both modes requested the same 353,894,400 bytes (337.5 MiB) of
stage buffers. This is requested owner size, not a unique physical-backing
reconciliation.

| Measure | Pinned median | Pageable median | Paired pinned-minus-pageable median | Paired bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Prompt | 13,189.5 ms | 12,476.4 ms | −0.31% | −0.64% to +231.02% |
| Decode | 14,102.1 ms | 13,840.0 ms | +2.30% | −1.27% to +2.87% |
| Request | 27,291.6 ms | 26,316.4 ms | +1.00% | −0.80% to +111.58% |

One pinned prompt in pair 1 took 41.299 seconds versus 12.476 seconds for its
pageable pair. It remains in the result and makes the three-pair intervals very
wide. Tracing was enabled, and CPU/GPU clocks and energy were not qualified;
these timings do not establish either mode's product performance. No staging
mode is promoted.

The standard supervisor passed with its six-GiB effective-availability floor.
Minimum host `MemAvailable` was 22,648,008,704 bytes (21.10 GiB); minimum
effective cgroup headroom was 13,542,154,240 bytes (12.61 GiB). The successful
campaign used a 28-GiB `MemoryMax`, with no OOM events.

Two excluded/incomplete starts are retained. The initial unsupervised attempt
was interrupted during model startup before any paired request; it is not a
measurement. The 22-GiB supervised attempt completed pair 0, then was safely
aborted when effective headroom sampled at 5.97 GiB, below the six-GiB guard,
before pair 1 completed. Host availability stayed above 20.9 GiB and no cgroup
OOM event occurred. The complete, guarded three-pair result is under
`experiment-28g/` with telemetry under `supervisor-28g/`.

The exact model artifacts remain under `~/models/`; their identities and the
engine/prompt hashes are retained in [`artifact-identities.json`](artifact-identities.json).
The full per-arm results and logs preserve the failed/aborted cells as well as
the successful campaign. This adds a Q2_0 transfer-correctness cohort, not a
cross-model performance conclusion or Phase 3 completion.

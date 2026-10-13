# Long-context retrieval and sustained streaming — Orin — 2026-10-13

This is partial Phase 7 evidence for one opt-in IQ1_M serving profile. It does
not qualify other models, defaults, or general capacity. The profile used the
Q6_K warp-dequant option, accepted-only MTP4 adaptation at cadence 4, FP16 KV,
3,000 requested expert-cache slots (3,903 actual slots), eight workers, dynamic
clocks, and an 8K/16K/32K configured context. The model, expert profile and MTP
artifacts stayed under `~/models/` or their existing local paths.

## Long-context recall and recovery

One exact-token prompt at each configured context placed three independent
markers near 10%, 50%, and 90% of the prompt. The answer had to return each
marker exactly once and in order; a subsequent short request on the same
service had to return `RECOVERED`.

| Configured context | Actual prompt | Recall | Same-service recovery | Minimum host availability |
| ---: | ---: | --- | --- | ---: |
| 8,192 | 7,498 | Pass | Pass | 13.35 GiB |
| 16,384 | 15,003 | Pass | Pass | 13.06 GiB |
| 32,768 | 30,032 | Pass | Pass | 12.67 GiB |

All three runs were supervised with a 28-GiB cgroup ceiling and six-GiB
host/effective availability floor. They had no OOM events or floor breach;
clocks were observed dynamically, EMC access was denied, and energy was not
process-attributed. The first 8K attempt failed before service startup due to a
test-driver import-path error; it is retained in `ctx8192/`. The corrected
isolated rerun is `ctx8192-retry/` and passed. This result qualifies only these
exact prompts, profile, and artifacts.

## Sustained cache-reuse stream

The same service first completed a 512-token warmup and a 7,498-token
retrieval precondition. It then completed 2,401.5 seconds of streamed requests
with 1,579 requests and zero failures. Independent post-run inspection confirmed
that every response contained the three markers exactly once and in order.
Median request elapsed time was 1.56 s and median first-visible-token latency
was 0.247 s. Every request reused 7,491 prompt tokens; this is a cache-reuse
streaming soak, not a fresh-prefill or capacity-latency measurement. Minimum
host/effective availability was 13.34 GiB, with zero observed cgroup OOM events.

The tegrastats CPU/Tj temperature rose during initial load and prefill, then
remained between 75.5 and 77.4 °C from 11:52:57 through the end at 12:24:01
(about 31 minutes). The measured request loop began around 11:43, leaving more
than 30 minutes of the 40-minute loop after that stable-temperature point.
The GPU reported 99% utilization. CPU and GPU frequency observations stayed
under dynamic policy; the EMC frequency was not readable. Board rail readings are
retained but are not process-attributed energy.

The workload checks exact retrieval and service continuity under cache reuse.
It does not test concurrent requests, cancellation, vision, teardown after
repeated model reload, quality beyond these marker checks, or a second model.
Phase 7 remains in progress.

Raw request rows, engine output, tegrastats, supervisor telemetry and result
JSON files are retained in this directory. The service binary SHA256 is
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.

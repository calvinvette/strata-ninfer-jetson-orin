# Q2_0 worker × transfer rerun (2026-10-12)

This follow-up checks the prior 4-worker/mapped persistent-state anomaly and
screens trace-free response time for the existing worker × expert-transfer
factorial. The model, pack, 512-prompt/64-generation workload, 8,192 context,
3,000 cache slots, two-token speculation setting, candidate binary and six-GiB
host-availability floor match the 2026-10-11 screen. No model or build artifact
is stored in this repository.

## Correctness gate

The seeded randomized matrix used 4/8 CPU pool workers, mapped/pread expert
transfer, and three process repetitions per cell. The accepted-prefix tracing
rerun passed all 12/12 cells: HTTP/request completion, output IDs, cache
capacity, accepted-prefix records and final persistent-state fingerprints
matched. The earlier 4-worker/mapped mismatch did not reproduce. The supervised
minimum host `MemAvailable` was 18,751,746,048 bytes (17.47 GiB); the six-GiB
floor was preserved.

## Trace-free timing screen

A separate randomized three-repetition matrix disabled trace instrumentation.
All 12 requests completed with the same output hash and 3,000 actual cache
slots. Per-cell median request times were:

| Pool workers | Mapped | Pread |
| ---: | ---: | ---: |
| 4 | 15,605.3 ms | 16,431.0 ms |
| 8 | 15,610.9 ms | 16,476.7 ms |

The three-pair mapped-minus-pread paired request deltas were −3.99%, +5.29%,
and +14.52% at four workers; at eight workers they were +193.93%, +6.34%, and
−8.37%. The extreme first pair demonstrates cache/order sensitivity. The
bootstrap 95% median interval for the mapped/pread interaction was −197.92 to
+22.88 percentage points. Worker effects were also inconclusive, with intervals
spanning zero. This is a screening result, not a confirmed effect; no worker
count or transfer default is recommended. No seven-pair confirmation was
triggered by this noisy screen.

The six-GiB supervisor passed with minimum host availability of
19,034,284,032 bytes (17.73 GiB). The supervisor sampled dynamic clocks and
tegrastats; no clocks were controlled, energy was not measured, and no physical
transfer-byte effect is inferred from these timings. The model, engine binary,
commands, raw request records and supervisor telemetry are retained alongside
this report.

## Artifacts

- `correctness/`: 12 traced cell records and matrix result.
- `timing/`: 12 trace-free cell records, paired summaries and factorial
  bootstrap intervals.
- `timing-supervisor/`: six-GiB guard, memory and clock samples, tegrastats.

Phase 6 remains in progress. This screen does not close held-out confirmation,
quality, sustained service or multi-objective profile selection.

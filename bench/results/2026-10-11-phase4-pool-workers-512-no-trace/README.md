# CPU expert-pool worker timing screen without tracing — Orin — 2026-10-11

This randomized three-block screen compared 1, 2, 4 and 8 CPU expert-pool
workers on the IQ1_M Coder model with Q2_0 MTP, CPU prefill sharing disabled,
a 512-token prompt, eight generated tokens and a fixed requested 3,000-slot
expert cache. Every process performed a distinct 512-token warmup before the
measured request. All 12 cells passed the API request and reported 3,903 actual
cache slots. Output hashes matched across every worker count. The prior
trace-enabled screen for this exact workload also matched full accepted-prefix
state; this timing screen intentionally did not collect state traces.

| Workers | Median prompt (ms) | Median decode (ms) | Median request (ms) | Paired request delta vs 8 workers |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 17,362.7 | 1,744.7 | 19,102.4 | +6.60% to +8.90% |
| 2 | 17,139.3 | 1,380.7 | 18,518.8 | +5.02% to +5.18% |
| 4 | 17,018.3 | 979.0 | 18,001.1 | +1.76% to +2.84% |
| 8 | 16,857.8 | 749.9 | 17,607.1 | baseline |

The median request times order monotonically across the tested worker counts,
with eight workers fastest in all three paired blocks. The resampled 95%
bootstrap intervals are based on only three independent blocks and reduce to
the observed paired-delta ranges above; they are screening intervals, not a
confirmation claim. Timing medians are per request. No default changed.

The test verified that all 12 generated server configs and engine logs had no
`STRATA_TRACE`, state-hash, integration-trace or accepted-prefix-trace flags,
including inherited shell environment values. Minimum host `MemAvailable` was
14,214,795,264 bytes (13.24 GiB). Tegrastats observed CPU frequencies from 729
to 2,201 MHz and junction temperatures from 49.4 to 57.9 C. GPU frequency and
EMC frequency were unavailable; GR3D utilization ranged from 0% to 99%.
Energy was not measured, and thermal equilibrium was not established.

The engine SHA256 was
`3ed52e6e0f845415b8fb2f2c15577f4b90efe49be72e2866d0dc961dbb0c95b0`.
The base config and exact workload are retained here. Raw per-cell API output,
engine logs, worker order, supervisor memory samples and tegrastats are under
`experiment/` and `supervisor/`. This is one workload/cache/prefill-sharing
policy; held-out prompts, quality and confirmation repetitions remain open.

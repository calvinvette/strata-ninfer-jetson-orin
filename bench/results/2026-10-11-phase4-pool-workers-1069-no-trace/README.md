# CPU expert-pool worker screen on a held-out prompt — Orin — 2026-10-11

This randomized three-block no-trace screen compared 1, 4 and 8 workers on a
1,069-token prompt with eight generated tokens. It used the same IQ1_M Coder
model, Q2_0 MTP runtime, CPU-prefill-sharing-disabled policy and requested
3,000-slot expert cache as the 512-token screen. Each process had a distinct
1,069-token warmup prompt. All nine requests passed; every process admitted
3,903 actual cache slots and the output hashes matched across worker counts.

| Workers | Median prompt (ms) | Median decode (ms) | Median request (ms) | Paired request delta vs 8 workers |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 32,774.5 | 1,699.8 | 34,474.3 | +4.82% to +5.25% |
| 4 | 32,274.6 | 948.5 | 33,223.1 | +1.01% to +1.60% |
| 8 | 32,084.3 | 743.8 | 32,828.1 | baseline |

Eight workers were fastest in all three paired blocks. The three-block
bootstrap intervals reduce to the observed paired-delta ranges and are only
screening uncertainty. This repeats the worker ordering from the separate
512-token screen, but the margin is smaller on the longer prefill. No default
changed. This timing-only run checked API output and cache capacity, not
accepted-prefix state; the matching 512-token correctness screen covered that
state contract for its own workload only.

Minimum host `MemAvailable` was 14,290,157,568 bytes (13.31 GiB). Tegrastats
observed CPU frequencies from 729 to 2,201 MHz and junction temperatures from
50.5 to 58.8 C; GPU and EMC frequencies were unavailable, with GR3D utilization
from 0% to 99%. Energy was not measured and thermal equilibrium was not
established. One prompt/process cell is not held-out quality confirmation.

The engine SHA256 was
`3ed52e6e0f845415b8fb2f2c15577f4b90efe49be72e2866d0dc961dbb0c95b0`.
The base config and workload are retained here; raw API responses and logs,
randomized orders, memory samples and tegrastats are under `experiment/` and
`supervisor/`. No model or build products are included.

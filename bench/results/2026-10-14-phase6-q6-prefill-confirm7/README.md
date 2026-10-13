# Held-out Q6 prefill-chunk confirmation

This seven-block same-day confirmation held the IQ1_M Q6 warp-dequant,
accepted-only MTP4, FP16 KV, 8K context, eight workers, and `--expert-cache
3000` budget fixed. It compared prefill chunks 32 and 128 on the distinct
1,069-token historical-repeat prompt. Each process performed one warmup and one
measured request; the measured request used exactly 1,069 prompt tokens and
generated exactly eight tokens with prompt caching disabled. Arm order was
randomized within each pair (seed `20261014128`). Both arms used 3,903 resident
expert slots in every block.

| Measure | Chunk 32 median | Chunk 128 median | Paired median change (95% bootstrap interval) |
| --- | ---: | ---: | ---: |
| Prompt throughput | 22.0 tok/s | 65.8 tok/s | +196.4% (+196.4%, +204.6%) |
| Client request time | 49.1 s | 16.7 s | −65.7% (−66.5%, −65.6%) |

All seven paired prompt-throughput deltas favored chunk 128. All 14 processes
passed the workload and supervisor checks. Minimum available host memory was
13.10 GiB; minimum effective admission headroom was 10.60 GiB. Cgroup `oom`,
`oom_kill`, `high`, and `max` counters stayed at zero. CPU/GPU clocks were
observed under dynamic policy; EMC readback was denied, and energy was not
measured. Results use one short-generation workload and do not estimate tail
latency or energy.

The baseline output was stable across its seven blocks, and the candidate
output was stable across its seven blocks, but their generated eight-token text
prefixes differed: baseline began “A computer processes information through a
complex,” while chunk 128 began “A computer processes information through a
sophisticated,”. Thus this confirms a prompt-path performance effect on the
held-out prompt, but not output parity or comparative task quality. The short
generation is not enough to judge semantic quality. No default or profile is
promoted; the separate full-task quality screen covers a different prompt.

An initial launch nested a second supervisor under the same board lock and
stopped before any model process started. It is retained in
`attempt-01-board-lock/` as an infrastructure failure and excluded. The measured
campaign ran directly inside one 28-GiB systemd scope, with each child run
acquiring the board lock and retaining its own telemetry.

The raw campaign, per-arm API responses, logs, clocks and memory telemetry are
retained here. Models remain in `~/models/`.

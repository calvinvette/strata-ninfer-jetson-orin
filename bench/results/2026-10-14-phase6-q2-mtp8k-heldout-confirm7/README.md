# Q2_0 8K held-out MTP4 confirmation — Orin — 2026-10-14

This seven-pair randomized confirmation compared MTP window 4 with MTP off on
one held-out near-limit retrieval prompt. Each arm used a fresh service, an
8,192-token context, FP16 KV, 3,000 expert slots, no prompt cache, no adaptive
swaps, 512-token prefill chunks, and the same no-trace configuration apart
from MTP selection. Each service received one separate 512-token warmup and one
measured request. The prompt was exactly 7,505 rendered tokens; generation was
capped at 48 tokens. Every answer contained the three expected codes in order
and all seven paired API responses were identical.

Within-pair order was randomized using seed `2026101407`: MTP off first in
blocks 0, 1, 2, 4 and 5; MTP4 first in blocks 3 and 6. Each response generated
40 tokens. MTP4 offered 36 drafts and accepted 27 in every pair. Paired MTP4
versus off deltas were:

| Measure | Per-block deltas | Median |
| --- | --- | ---: |
| Decode throughput | +10.52%, +17.09%, +10.28%, +19.60%, +20.70%, +18.92%, +11.87% | +17.09% |
| Client first-visible TTFT | +9.34%, +8.36%, +10.72%, +8.86%, +10.84%, +11.50%, +11.53% | +10.72% |
| Client total request time | +8.11%, +6.79%, +9.45%, +7.15%, +8.93%, +9.59%, +10.14% | +8.93% |
| Prompt throughput | −8.54%, −7.72%, −9.70%, −8.18%, −9.82%, −10.34%, −10.37% | −9.70% |

The paired bootstrap 95% interval for the median decode-throughput delta was
`+10.52%` to `+19.60%`. MTP4 therefore improved decode throughput on this
prompt, but the task was prefill-dominated: it raised TTFT and total request
time in all seven pairs. This is a decode-only tradeoff, not an end-to-end win;
no profile or default is promoted. The result applies only to this Q2_0 artifact,
prompt, context, and runtime configuration.

All 14 fresh-service cells passed under separate 28-GiB systemd scopes. Minimum
host availability was 16.854 GiB and minimum effective admission availability
was 6.021 GiB; the six-GiB floor was maintained. Sampled cgroup `low`, `high`,
`max`, `oom`, and `oom_kill` counters remained zero. Clocks were observed
read-only and remained dynamic; EMC access was unavailable. Energy was not
process-attributed, so no energy-per-token result is reported. The model and
runtime packs remained under `~/models/strata-orin-validation/`. The tested
candidate executable SHA256 was
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`.

The held-out workload JSON SHA256 is
`622f06971e2c94a3c58d3b4b4ee640463497b6482a43f1ba0eae1561172833b9`. Its
markers are `AMBER-QUARTZ-618`, `SILVER-MEADOW-243`, and `INDIGO-LANTERN-907`.
The campaign, per-request records, configs, engine logs, supervisor memory
samples, and tegrastats are retained under [`campaign-retry1`](campaign-retry1/).
An earlier setup attempt is retained under `campaign/`; it failed before
starting any model service because an outer supervisor held the board lock.
That attempt is excluded from timing evidence. `SHA256SUMS.txt` covers the
workload, report, and campaign artifacts.

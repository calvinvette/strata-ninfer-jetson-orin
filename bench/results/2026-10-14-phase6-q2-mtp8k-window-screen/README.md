# Q2_0 8K MTP4 versus MTP-off screen — Orin — 2026-10-14

This three-block randomized screen compared native MTP window 4 with MTP off
on the same Q2_0 retrieval task. Each arm used a fresh service, 3,000 expert
slots, FP16 KV, an 8,192-token context, 512-token prefill chunks, zero prompt
cache, no adaptive swaps, and the same no-trace server configuration apart from
MTP selection. A separate 512-token/one-token request warmed each process. The
measured request used the exact 7,498-token `multineedle-8192` prompt and a
48-token generation cap; natural-stop acceptance was explicitly enabled. All
six measured requests stopped at 41 tokens and returned identical content.

The randomized order was MTP4 then off in blocks 0 and 1, and off then MTP4 in
block 2. MTP4 drafted 33 and accepted 29 in each block. Paired candidate/off
deltas were:

| Measure | Block 0 | Block 1 | Block 2 | Median |
| --- | ---: | ---: | ---: | ---: |
| Decode throughput | +28.78% | +27.16% | −3.98% | +27.16% |
| Client first-visible TTFT | +7.63% | +7.83% | +4.79% | +7.63% |
| Client total request time | +5.64% | +5.74% | +4.77% | +5.64% |
| Prompt throughput | −7.22% | −7.30% | −4.59% | −7.22% |

The three-pair bootstrap interval for median decode delta was −3.98% to
+28.78%. Each arm's median decode rate was 5.353 versus 4.218 tok/s; median
client TTFT was 134.05 versus 126.37 seconds; median total request time was
141.70 versus 135.25 seconds (MTP4 versus off). The task is prefill-dominated,
so these results do not establish a decode-heavy workload effect. The decode
interval includes no change, and TTFT and total request time were slower in all
three pairs. No held-out timing confirmation is justified by this screen; no
setting or default is promoted.

All six supervised cells passed the six-GiB floor. Minimum host availability
was 16.80 GiB and minimum effective admission availability was 6.19 GiB. The
28-GiB systemd scope's sampled `low`, `high`, `max`, `oom` and `oom_kill`
counters remained zero. Clock observations were read-only and dynamic; EMC
frequency access was denied. Board power rails were not request-attributed, so
energy/token is unavailable. The Q2_0 source is `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0` (GGUF shards
`...00001-of-00002.gguf` and `...00002-of-00002.gguf`); the runtime pack,
expert profile and MTP pack remained under `~/models/strata-orin-validation/`. The candidate `strata` binary SHA256 is
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.

Raw campaign, request output, configs, engine logs, memory samples and
tegrastats are retained in
[`paired-natural`](../2026-10-14-phase6-q2-mtp8k-window-screen-paired-natural/).
The earlier attempts are retained alongside it: an output-path collision;
a board-lock collision from nesting supervisors; one unsupported
accepted-only-swap configuration; one malformed MTP-off argument list; and
one initial run where the strict generation-cap validator rejected the
correct 41-token natural answer. That last run was interrupted after the
harness failure and is not timing evidence. These setup/harness attempts are
not included in the six passing cells. `SHA256SUMS.txt` covers this report and
the raw attempt and final-screen artifacts.

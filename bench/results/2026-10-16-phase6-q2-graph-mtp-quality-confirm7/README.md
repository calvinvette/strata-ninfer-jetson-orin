# Q2_0 graph × MTP2 task-quality confirmation — 2026-10-16

This seven-block randomized confirmation reran the captured/eager decode ×
MTP-off/window-2 comparison on the already-qualified processor explanation task.
It addresses the task-quality failure in the earlier [512/64 graph × MTP
confirmation](../2026-10-14-phase6-q2-graph-mtp-confirm7/README.md): all 28
responses now pass the task rubric, so the performance comparison is qualified
for this prompt and configuration.

The exact user message is in `workloads.json` (SHA256
`18d3bd6aa352c3d8f5f590c8f852b21f40baf0b22380910fee2013d2f510a673`). It
renders to 2,094 prompt tokens. The task asks for at least 200 words, opening
with `Processor:`, an explanation of fetch/decode/execute, RAM, binary data,
input and output, and the exact arithmetic statement `17 x 19 = 323`. Every
response stopped naturally after 293 tokens, contained 234 whitespace-delimited
words, passed all rubric checks, and was byte-identical across all 28 arms.
This is a focused task check, not a general language-quality score.

Each fresh service used the same local Q2_0 two-shard model, MTP runtime pack,
3,000 resident expert slots, FP16 KV, 8K context, prefill chunk 512, zero prompt
cache, eight pool workers, accepted-only adaptation cadence 4, and 28-GiB
supervisor. A distinct 512-token/one-token request warmed each service before
the measured request. Trace instrumentation was disabled. The only factors
were CUDA Graph capture (captured/eager) and MTP (off/window 2). Conditions
were randomized within each of seven independent blocks, with one process per
cell. The binary SHA256 was
`fd9c010cb5e126dfa1f272d6c2864830df25a67c08c5aacc69ea4c98d5c2a29b`.

| Condition | Median client time (s) | Median client TTFT (s) | Median prompt (tok/s) | Median decode (tok/s) | Drafts offered / accepted per run |
| --- | ---: | ---: | ---: | ---: | ---: |
| Captured, MTP off | 61.949 | 25.928 | 81.5 | 8.1 | 0 / 0 |
| Eager, MTP off | 61.784 | 25.771 | 82.0 | 8.1 | 0 / 0 |
| Captured, MTP2 | 64.433 | 26.752 | 79.0 | 7.7 | 153 / 97 |
| Eager, MTP2 | 64.669 | 26.603 | 79.4 | 7.7 | 153 / 97 |

The paired change is candidate/baseline within each block. Intervals are 95%
percentile bootstrap intervals over seven independent paired ratios (20,000
resamples), not token-level samples. Negative latency is faster; positive
throughput is faster.

| Contrast | Client time | Client TTFT | Prompt throughput | Decode throughput |
| --- | ---: | ---: | ---: | ---: |
| Captured vs eager, MTP off | −0.04% [−0.80, +0.97] | +0.04% [−1.80, +1.80] | +0.12% [−1.83, +1.73] | 0.00% [−1.23, 0.00] |
| Captured vs eager, MTP2 | +1.11% [−1.05, +2.07] | −0.49% [−1.46, +1.03] | +0.38% [−1.00, +1.51] | 0.00% [−3.85, +1.30] |
| MTP2 vs off, captured | +4.12% [+3.52, +6.36] | +2.97% [+2.21, +3.98] | −2.83% [−3.78, −2.18] | −6.10% [−8.54, −2.50] |
| MTP2 vs off, eager | +3.86% [+1.91, +5.61] | +3.41% [−0.56, +5.30] | −3.41% [−4.99, +0.50] | −4.94% [−6.10, −3.70] |
| Capture × MTP2 interaction | +0.37% [−1.06, +1.58] | −0.53% [−2.61, +2.57] | +0.26% [−2.59, +2.65] | 0.00% [−4.18, +1.30] |

Neither capture main effect nor the capture × MTP interaction excludes no
change. MTP2 was slower in both routes: captured request time rose 4.12% and
decode throughput fell 6.10%, with both paired intervals excluding zero.
MTP2 accepted 97 of 153 drafts in each run, but acceptance did not produce a
request-time or decode-throughput win for this 2,094/293 workload. Do not
promote capture or MTP2 from this cell; keep the existing opt-in/default policy.

All 28 supervised runs passed the 6-GiB host floor and 3-GiB separate admission
reserve. Minimum host availability was 16.925 GiB and minimum admission
availability was 11.630 GiB. The 28-GiB cgroups recorded zero `low`, `high`,
`max`, `oom` and `oom_kill` events. Across 3,012 one-second samples, CPU clocks
ranged from 729.6 MHz to 2,201.6 MHz and GPU clocks from 306 MHz to 1,300.5
MHz; EMC clock reads were unavailable. Clocks were observed dynamically and
not controlled. The OS file cache was shared and not flushed. Board energy
rails are not process-attributed, so energy per request/token is not reported.

The complete API responses, engine logs, service configs, cgroup/host memory
samples, clocks and tegrastats are retained in `run-confirmation/`. Model, PLE,
profile, MTP and prompt identities are listed in `artifact-identities.json`. The
paired effect plot is available as [`paired-effects.svg`](paired-effects.svg);
rebuild it with `python3 .../plot_effects.py`.
The first `run/` directory retains a harness-only failed attempt: its quality
answer passed, but the first runner incorrectly looked for `finish_reason` in
a streamed API response that omits it. The engine request metrics recorded the
natural `stop`; the gate now reads that authoritative counter. This attempt is
excluded from all 28-cell estimates.

Reproduce on Orin1 with the local Q2_0 and MTP artifacts in `~/models/`:

```sh
python3 bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/confirm7.py \
  --output bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/run-confirmation \
  --blocks 7 --seed 202610164 --run
python3 bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/analyze_confirm7.py
python3 bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/plot_effects.py
```

The runner refuses to overwrite an existing output. `analysis.json` contains
per-cell measurements, per-block ratios, bootstrap intervals and memory-event
maxima; `run-confirmation/campaign.json` contains the randomized schedule and
commands. This result is scoped to one Q2_0 artifact, processor task, context,
cache/adaptation policy and runtime build. It does not close Phase 6 or qualify
other workloads, KV formats, MTP windows or a serving profile.

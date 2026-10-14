# Q2_0 graph × MTP2 held-out confirmation — 2026-10-14

This seven-block randomized confirmation followed the three-block graph × MTP
screen. It crossed captured/eager decode with MTP off/window 2 on one distinct,
exact 512-token `heldout_blue` prompt and 64 generated tokens. Each of the 28
cells used a fresh service, the same separate 512-token/one-token warmup,
accepted-only swap cadence 4, 3,000 expert-cache slots, FP16 KV, prefill chunk
512 and zero prompt-cache capacity. Trace instrumentation was disabled. The
candidate binary SHA256 was
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.

All 28 requests used exactly 512 prompt and 64 completion tokens. The API
response text was byte-identical in every block and across all conditions.
Every MTP2 process offered 33 drafts and accepted 24. All cells used 3,000
resident expert slots and FP16 KV. Every supervised run passed the six-GiB
host-availability floor and separate three-GiB admission reserve; the minimum
host availability was 16.85 GiB and minimum admission availability was
13.12 GiB. Cgroup `low`, `high`, `max`, `oom` and `oom_kill` event counters
remained zero.

The paired effects below are candidate/baseline ratios within each randomized
block, bootstrapped over the seven independent process pairs (20,000 resamples).
Negative latency changes mean faster; positive throughput changes mean faster.

| Contrast | Client request time | Client TTFT | Prompt throughput | Decode throughput |
| --- | ---: | ---: | ---: | ---: |
| Captured vs eager, MTP off | −0.69% [−2.37, +1.19] | −1.68% [−2.95, +1.31] | +1.93% [−1.20, +3.14] | +0.00% [−1.82, +1.96] |
| Captured vs eager, MTP2 | −0.23% [−3.59, +6.21] | −1.86% [−6.94, +14.59] | +1.22% [−13.24, +7.69] | +1.85% [−3.77, +1.89] |
| MTP2 vs off, captured | +6.12% [+0.38, +7.12] | +11.11% [+1.02, +13.14] | −10.33% [−11.75, −1.05] | −1.82% [−3.77, 0.00] |
| MTP2 vs off, eager | +0.44% [−0.75, +6.62] | +5.68% [−1.78, +17.37] | −5.18% [−15.11, +2.10] | +0.00% [−3.64, +1.89] |
| Capture × MTP2 interaction | +1.73% [−3.52, +6.11] | +1.84% [−6.08, +13.12] | −2.26% [−12.18, +6.63] | −0.07% [−3.77, +1.89] |

The graph/eager effects and graph × MTP interaction include no change for all
four outcomes. MTP2 did not improve decode throughput. For this prompt and
configuration, MTP2 increased captured-route request time and TTFT and reduced
prompt throughput; the eager-route intervals include no change. The 24/33
accepted drafts therefore did not translate into a request-time win in this
cell. Keep the current defaults and MTP opt-in behavior unchanged.

These are performance results for one held-out short workload and one Q2_0
artifact. The 64-token output is not task-quality evidence or token-ID/state
parity evidence. MTP quality and accepted-prefix state are checked separately
in the [Q2_0 task-quality](../2026-10-14-phase5-q2-mtp-quality/README.md) and
[accepted-prefix reports](../2026-10-13-phase5-q2-accepted-prefix/README.md).
Clocks were observed dynamically; the file page cache was shared and not
flushed. Energy rails are board-wide and cannot be attributed to these
requests, so no energy/token claim is made. The result does not qualify other
prompt lengths, KV formats, MTP windows, or profile combinations.

## Separate full-task quality check

The same held-out prompt was also run once in each of the four settings with a
1,024-token allowance. All four answers stopped naturally at 850 tokens (588
words), were byte-identical, and mentioned input, working memory and storage.
All four failed the task rubric's opening instruction: the answer began with
meta-commentary about the repeated-blue context instead of the memory
controller. A preceding 512-token allowance stopped mid-sentence in every arm
and is retained as incomplete. These are shared task failures, not a graph/MTP
quality difference; they do not qualify a serving profile. Full outputs and
supervisor telemetry are under `run/quality-full/`; capped attempts are under
`run/quality/`.

Raw per-cell API responses, server configs/logs, clocks, host/cgroup telemetry,
and tegrastats are retained under `run/`. The exact prompt IDs and source are
in `heldout-512.tokens` and `workloads.json`.

Reproduce with the local Q2_0 and MTP artifacts in `~/models/`:

```sh
python3 bench/results/2026-10-14-phase6-q2-graph-mtp-confirm7/prepare_workload.py
python3 bench/results/2026-10-14-phase6-q2-graph-mtp-confirm7/confirm7.py \
  --output bench/results/2026-10-14-phase6-q2-graph-mtp-confirm7/run \
  --blocks 7 --seed 202610143 --run
python3 bench/results/2026-10-14-phase6-q2-graph-mtp-confirm7/analyze_confirm7.py
```

The schedule randomizes four conditions within each block and runs them
sequentially under separate 28-GiB cgroups with the six-GiB physical host
floor. No clocks or services are changed outside those owned by the run.

# Q2_0 MTP-window × KV-format screen — Orin — 2026-10-14

This same-day Phase 6 screen compared MTP windows 0/2/3/4 with FP16 and int8
KV on one held-out semantic task. Each format used three randomized blocks of
fresh services. Every cell performed one distinct 512-token warmup, then one
512-token prompt / 64-token generation request. The prompt SHA256 is
`860c3caebc8317ff48d89a528006fce9bba8e3fa95b967a6c59528f0f5f0b7a2`; the
candidate binary SHA256 is
`5a72dbad8a79782a7cd778ab222fdcfe82f3665b25923767215f0f465bbcd213`.
Both campaigns used the Q2_0 shards and tokenizer from
`~/models/strata-orin-validation/`, captured graphs, an 8K context, a 3,000-slot
expert profile, eight pool workers, no adaptive swaps, prompt cache disabled,
and the existing three-GiB VRAM reserve argument. The runs were trace-free for
timing and had dynamic clocks.

All 24 fresh-service cells passed. Within each format and block, the API output
was identical across MTP windows, and the engine reported the requested KV
format and 3,000 actual expert slots. Median paired effects versus MTP-off were:

| KV format | MTP window | Decode rate change (paired 95% interval) | TTFT change | Total request change | Drafts / accepted per block |
| --- | ---: | ---: | ---: | ---: | ---: |
| int8 | 2 | +8.78% (+7.40%, +13.76%) | +12.09% | +0.54% | 36 / 27 |
| int8 | 3 | +8.43% (+1.79%, +14.01%) | +1.51% | −5.01% | 56 / 35 |
| int8 | 4 | −5.98% (−8.15%, −3.21%) | +6.31% | +4.86% | 75 / 38 |
| FP16 | 2 | +2.77% (+1.67%, +4.62%) | +6.06% | +1.62% | 38 / 25 |
| FP16 | 3 | +2.47% (+1.55%, +4.31%) | +0.38% | −0.98% | 58 / 36 |
| FP16 | 4 | −9.83% (−11.98%, −8.17%) | +12.24% | +10.76% | 81 / 36 |

Intervals bootstrap the three whole paired blocks; they do not treat tokens as
independent samples. The paired decode-rate difference-in-differences
(int8-window effect minus FP16-window effect) was +7.10 percentage points for
window 2, +6.88 for window 3, and +6.00 for window 4. These are exploratory:
all int8 blocks ran before the FP16 blocks, so KV-format order was not
randomized. The small sample, dynamic clocks, and large first-block TTFT/request
outlier for int8 window 4 further limit the interaction estimate. This does not
qualify a KV/MTP profile or a full-task quality result. No default changed.

Minimum physical host availability and effective admission availability were
16.914/6.278 GiB for int8 and 16.842/6.454 GiB for FP16. All sampled cgroup
high, max, OOM and OOM-kill counters remained zero. The six-GiB host floor and
separate workspace reserve were preserved. Energy was not request-attributed.

The raw [int8 campaign](../2026-10-14-phase6-q2-int8-mtp-window-screen/run-retry1/)
and [FP16 campaign](../2026-10-14-phase6-q2-fp16-mtp-window-screen/run/)
include configs, request records, engine logs, supervisor memory samples and
tegrastats. The first int8 setup attempt is retained at
[run/](../2026-10-14-phase6-q2-int8-mtp-window-screen/run/) and excluded: the
static-cache screen disabled swaps but inherited `--adapt-accepted-only`, so
argument validation exited before model load. The screen's shared argument
normalizer now removes that incompatible flag when disabling adaptive swaps;
focused tests pass.

Reproduction uses `tools/integration/mtp_window_screen.py` with the retained
per-format config/workload/warmup JSON and `--windows 0 2 3 4 --blocks 3
--seed 20261014`, wrapped in `run_control.py` under a 28-GiB systemd scope.
`analysis.json` contains block-level deltas, bootstrap intervals, interaction
contrasts, memory floors and artifact identities. `SHA256SUMS.txt` covers the
summary, analysis, modified harness/tests and retained raw campaign files.

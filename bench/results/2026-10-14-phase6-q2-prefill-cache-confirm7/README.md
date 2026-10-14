# Q2_0 prefill-chunk × expert-cache confirmation — Orin — 2026-10-14

This seven-block randomized 2×2 confirmation crossed prefill chunks 32/128
with expert-cache budget arguments 3,000/5,000. It used one fresh service per
cell and one warmup plus three measured requests for the held-out 512-token
retrieval-plus-arithmetic prompt. The service profile was Q2_0, 8,192 context,
FP16 KV, MTP max 4 with speculation depth 2, eight pool workers, mmap expert
reads, and prompt cache disabled. The input files are the same Q2_0 model/pack
paths and workload as the adjacent
[worker × transfer confirmation](../2026-10-14-phase6-q2-worker-transfer-confirm7/README.md);
the workload SHA256 is
`c80ade67777ad08470fb9bd61ffa75d294af64e7958af6e9e25792103970b9e7`.
The candidate executable SHA256 is
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`.
Models and packs remained under `~/models/`.

All 84 measured responses returned exactly
`EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`.
Each had 512 prompt tokens and 47 completion tokens. The independent suffix
check is `618 + 243 + 907 = 1768`.

| Cache budget argument | Prefill chunk | Median request time | Median prompt rate | Median decode rate |
| ---: | ---: | ---: | ---: | ---: |
| 3,000 | 32 | 44,757 ms | 12.7 tok/s | 10.9 tok/s |
| 3,000 | 128 | 25,618 ms | 24.0 tok/s | 11.0 tok/s |
| 5,000 | 32 | 44,400 ms | 12.9 tok/s | 9.9 tok/s |
| 5,000 | 128 | 26,259 ms | 24.0 tok/s | 10.0 tok/s |

The request-time measure is engine-reported prompt plus decode milliseconds;
the cell statistic is the median of three requests. Paired effects compare
within each independent randomized block, with 100,000-resample bootstrap
intervals for the median block effect. Negative request-time changes mean
faster.

| Contrast | Median effect | Paired block bootstrap 95% interval |
| --- | ---: | ---: |
| Chunk 128 vs 32 at 3,000 budget | −42.65% request time | −43.28% to −39.13% |
| Chunk 128 vs 32 at 5,000 budget | −40.86% request time | −41.95% to −40.04% |
| Chunk 128 vs 32 prompt rate at 3,000 budget | +87.60% | +78.62% to +92.68% |
| Chunk 128 vs 32 prompt rate at 5,000 budget | +85.94% | +84.62% to +86.92% |
| 5,000 vs 3,000 budget at chunk 32 | +0.36% request time | −3.67% to +11.77% |
| 5,000 vs 3,000 budget at chunk 128 | +1.91% request time | +1.80% to +9.21% |
| Cache × chunk interaction | +1.33 percentage points | −1.72 to +3.23 points |

Chunk 128 reduced request time in every paired block at both cache arguments.
The decode rate changed little in the cell medians. The cache effect interval spans zero at chunk 32. At chunk 128, the 5,000
budget was slower by a median 1.91% (interval +1.80% to +9.21%), but the
actual-slot shortfalls make that comparison confounded. The cache × chunk
interaction interval includes zero. These results support chunk 128 as a strong
candidate for this exact Q2_0 task/profile, not as a default or general workload
result.

The requested 5,000 cache budget did not always admit 5,000 actual slots: the
engine reported 3,861, 3,939 and 4,853 slots in three cells. The other 25 cells
matched their requested slots; all 3,000-budget cells admitted 3,000. This
variation is retained and can affect cache comparisons, so the budget contrasts
and interaction remain limited screening evidence. No profile changed.

All 28 cells passed under the 28-GiB cgroup ceiling and the six-GiB host
availability floor. Minimum sampled host availability was 15,518,339,072 bytes
(14.45 GiB). Sampled cgroup high/max/OOM/OOM-kill counters were zero.
Tegrastats `tj` ranged from 50.2 to 59.8 °C. CPU/GPU clocks were dynamic.
Raw rail readings were retained, but energy was not attributed to requests.

The per-cell request text, timings, capabilities, actual cache slots,
supervisor records, memory samples, tegrastats and randomized orders are
retained here. Run `python3 analyze.py` from the repository root to recheck all
84 replies and regenerate `analysis.json`. `SHA256SUMS.txt` covers the result
files. To reproduce the seven blocks, use `run_confirm7.sh` under the same
28-GiB scope; it reuses the held-out workload and base configuration referenced
above.

This is a held-out confirmation for one task and one Q2_0 profile. It does not
qualify other prompt lengths, formats, concurrent requests or persistent-state
parity across chunk sizes. Phase 6 remains open for other workloads and
interactions.

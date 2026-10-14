# Q2_0 expert-cache × context confirmation — Orin — 2026-10-14

This seven-block randomized 2×2 screen varied requested expert-cache slots
(3,000/5,000) and configured context (8,192/16,384) on the Q2_0 model. Each
cell used an independent service, one warmup and three measured requests for
the same held-out 512-token retrieval-plus-arithmetic prompt. The profile used
FP16 KV, MTP max 4 with speculation depth 2, eight pool workers, mmap expert
reads, and no prompt cache. The requested cache slots and contexts were
confirmed in engine capabilities in all 28 cells.

All 84 measured responses exactly matched
`EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`.
Each response had 512 prompt tokens and 47 output tokens. An independent
suffix calculation gives `618 + 243 + 907 = 1768`.

The timing measure is the engine-reported prompt time plus decode time for a
request; the cell result is the median of its three requests. Effects compare
cell medians within each randomized block. The 95% intervals bootstrap the
seven paired block effects (100,000 resamples); negative values mean shorter
time. These are screening estimates for one held-out task, not broad workload
qualification.

| Contrast | Median effect | Paired block bootstrap 95% interval |
| --- | ---: | ---: |
| 5,000 vs 3,000 slots at 8K | −7.91% | −10.29% to −5.67% |
| 5,000 vs 3,000 slots at 16K | −11.20% | −16.81% to −9.66% |
| 16K vs 8K at 3,000 slots | −0.13% | −0.51% to +13.30% |
| 16K vs 8K at 5,000 slots | −1.52% | −2.02% to +2.67% |
| Cache effect at 16K minus cache effect at 8K | −1.75 percentage points | −11.14 to −0.92 points |

The larger cache reduced the measured request-time median in both tested
contexts. The context effect was inconclusive at both cache sizes. The cache ×
context interaction interval leans toward a larger cache effect at 16K, but this
single task and seven-block screen do not justify a default or a general
interaction claim. The measured cell medians were 25,083/25,523 ms at 3,000
slots and 8K/16K, and 23,014/22,832 ms at 5,000 slots and 8K/16K.

All cells passed the run supervisor under a 28-GiB cgroup ceiling and the
required six-GiB host-availability floor. Minimum sampled host availability
was 15,180,124,160 bytes (14.14 GiB); the floor was 6 GiB. No cell failed or
was unsupported. Tegrastats `tj` ranged from 49.1 to 58.6 °C. CPU/GPU clocks
were dynamic. Raw rail readings were captured, but energy was not attributed to
requests. The cell supervisor recorded cgroup memory and OOM counters; the
per-cell retained records are authoritative for those samples.

The run script, cell configurations, request responses, capabilities,
supervisor records, memory samples and tegrastats are retained here. Run
`python3 analyze.py` from the repository root to validate all cells and
regenerate `analysis.json`. `SHA256SUMS.txt` covers the result files. Models
and packs remain under `~/models/` and are not included.

This result closes only this seven-block held-out cache × context confirmation.
Phase 6 remains open for other workloads, cache sizes, KV formats, service
conditions and interactions; no default changed.

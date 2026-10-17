# Q2_0 cache × prefill confirmation — current source — Orin — 2026-10-17

This seven-block randomized confirmation retested the unresolved cache-size × prefill-chunk interaction on the current candidate binary. Each of the 28 cells used a fresh service, a separate 512-token warmup, and one measured 512-token retrieval-plus-arithmetic request. The crossed factors were exact expert-cache residency (3,000 or 3,500 slots) and prefill chunk (32 or 128). Q2_0, FP16 KV, MTP off, 8,192 context, eight workers, disabled prompt cache, no adaptive swaps, and the 28-GiB per-cell scope stayed fixed. The model files and packs remained under `~/models/strata-orin-validation`.

All 28 measured responses used 512 prompt tokens and 47 completion tokens and exactly returned `EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`. Every service admitted exactly its requested 3,000 or 3,500 slots. There were no sampled cgroup high/max/OOM/OOM-kill events. Minimum host availability was 17.38 GiB and minimum effective admission availability was 13.49 GiB, above the six-GiB floor. Dynamic GPU frequency ranged from 306 MHz to 1,300.5 MHz and CPU frequency from 729.6 MHz to 2,201.6 MHz; `tj` ranged from 48.25 to 57.31 °C. EMC readback was unsupported. Energy was not request-attributed.

| Cache slots | Prefill chunk | Median request time | Median prompt rate |
| ---: | ---: | ---: | ---: |
| 3,000 | 32 | 38.22 s | 15.1 tok/s |
| 3,000 | 128 | 20.74 s | 31.3 tok/s |
| 3,500 | 32 | 39.19 s | 14.8 tok/s |
| 3,500 | 128 | 21.33 s | 30.0 tok/s |

For the input rail `VIN_SYS_5V0`, request-window energy per 47 output tokens
had medians of 5.59, 3.12, 5.67 and 3.16 J in the same table order. The paired
chunk128 change was −44.23% at 3,000 slots (six supported pairs; 95% interval
−45.23% to −39.54%) and −44.29% at 3,500 slots (seven pairs; −46.42% to
−42.90%). The cache × chunk rail-energy interaction interval included zero.
The block-4 3,000-slot/chunk32 window is unsupported because its tegrastats
sample gap exceeded 2.5 seconds; all other 27 windows were integrated. These
are request-window rail estimates that include board idle/background activity,
not process-attributed energy, and no rails are summed.

| Contrast | Median paired change | Paired block bootstrap 95% interval |
| --- | ---: | ---: |
| Chunk 128 vs 32 at 3,000 slots | −45.85% request time | −47.07% to −45.08% |
| Chunk 128 vs 32 at 3,500 slots | −45.38% request time | −47.98% to −43.68% |
| 3,500 vs 3,000 slots at chunk 32 | +2.39% request time | +1.16% to +4.09% |
| 3,500 vs 3,000 slots at chunk 128 | +4.47% request time | −2.72% to +5.18% |
| Cache × chunk interaction | +0.20 percentage points | −4.18 to +1.44 points |

Chunk 128 reduced request time at both cache sizes in all seven blocks. The cache-size effect differed by chunk: the 3,500-slot cache was slower at chunk32, while its chunk128 interval included no change. The interaction interval also includes zero, so this run does not establish a cache × chunk effect. One block had a 70.25-second `cache3500-prefill32` request; the other six values ranged from 38.73 to 39.43 seconds; that cell passed the exact answer and all memory checks and is retained. Its in-request median GPU clock was 612 MHz, below the 714 MHz or higher observed in most other cells. This dynamic-clock outlier is a likely contributor, but these data do not prove causation. No result justifies changing a default.

`analysis.json` contains every per-cell request, clock, temperature and memory observation summary and the paired intervals. `rail-energy.json` and `rail-energy-pairs.csv` retain the request-window integrations and named-rail paired estimates. `artifacts.json` pins source, candidate binary, model and workload identity. `block-01/` through `block-07/` retain raw requests and telemetry; `SHA256SUMS.txt` covers the report artifacts. Reproduce from the repository root with:

```sh
bench/results/2026-10-17-phase6-q2-prefill-cache-current-source/run_confirm7.sh /tmp/q2-prefill-cache-current-source
python3 bench/results/2026-10-17-phase6-q2-prefill-cache-current-source/analyze.py
python3 bench/results/2026-10-17-phase6-q2-prefill-cache-current-source/analyze_rail_energy.py
```

This is evidence for the tested 512-token Q2_0 workload and MTP-off profile. It does not resolve the earlier cache-size reversal for other workloads or configurations. Phase 6 remains open.

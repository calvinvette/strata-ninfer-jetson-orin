# Q2_0 cache × prefill fixed-slot confirmation — Orin — 2026-10-15

This seven-block randomized confirmation revisits the Q2_0 expert-cache ×
prefill-chunk interaction. The prior seven-block run used 3,000/5,000 cache
arguments, but three 5,000-budget cells admitted fewer than 5,000 slots. This
run lowered the second budget to 3,500 and first screened it. The screen
admitted exactly 3,000 and 3,500 slots at both chunk sizes and all 12 measured
responses passed the held-out exact-answer check. The seven-block confirmation
then repeated the same 2×2 with seven randomized blocks and a fresh service per
cell.

Each of the 28 cells used one exact-length 512-token warmup and three measured
512-token retrieval-plus-arithmetic requests, with 47 output tokens each.
The fixed task returned
`EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`;
all 84 measured replies matched exactly. Every service admitted precisely the
requested cache size (3,000 or 3,500 slots). The profile used Q2_0, 8,192
context, FP16 KV, MTP max four/speculation depth two, eight workers, disabled
conversation cache, and no adaptive expert swaps. Models and packs remained
under `~/models/`.

| Cache slots | Prefill chunk | Median request time across seven block medians | Median prompt rate |
| ---: | ---: | ---: | ---: |
| 3,000 | 32 | 41,036 ms | 13.9 tok/s |
| 3,000 | 128 | 24,106 ms | 25.9 tok/s |
| 3,500 | 32 | 46,566 ms | 12.3 tok/s |
| 3,500 | 128 | 26,544 ms | 23.2 tok/s |

Paired effects use the seven block medians and 100,000-resample bootstrap
intervals for the median block effect:

| Contrast | Median effect | Paired 95% interval |
| --- | ---: | ---: |
| Chunk 128 vs 32 at 3,000 slots | −40.47% request time | −54.77% to −34.46% |
| Chunk 128 vs 32 at 3,500 slots | −42.42% request time | −43.10% to −41.50% |
| 3,500 vs 3,000 slots at chunk 32 | +12.53% request time | +3.43% to +16.37% |
| 3,500 vs 3,000 slots at chunk 128 | +9.67% request time | +0.73% to +33.89% |
| Cache × chunk interaction | −1.51 percentage points | −8.65 to +13.27 points |

Chunk 128 reduced median request time at both exact cache sizes in every block.
This supports chunk 128 for this Q2_0 task and profile. The initial three-
measured-request cells showed the 3,500-slot cache slower by 12.53% at chunk 32
and 9.67% at chunk 128. A separate seven-block confirmation with one measured
request per cell and read-only clock sampling found the 3,500-slot cache
slightly faster instead: −1.06% at chunk 32 (paired 95% interval −2.37% to
−0.44%) and −3.35% at chunk 128 (−4.16% to −2.37%). This opposite cache-size
direction means the cache effect is unresolved. The cache × chunk interaction
was also inconclusive in the initial run (−1.51 points, −8.65 to +13.27) and
small in the clock-sampled run (−1.17 points, −1.65 to −0.33). The difference
between these runs keeps the interaction exploratory; no cache/default claim
is promoted. Both per-block analyses are retained in `analysis.json` and
`clock-confirm-analysis.json`.

All 28 per-cell supervisors passed. Minimum host availability was 16.33 GiB;
minimum effective admission availability was 6.66 GiB, above the six-GiB floor
but with less margin than the host-only figure suggests. Across all samples,
cgroup high/max/OOM/OOM-kill counters were zero. Tegrastats `tj` ranged from
50.8 to 57.9 °C. The first seven-block run did not sample clock frequencies.
The separate clock-sampled confirmation had minimum host/admission availability
of 16.36/6.90 GiB and zero sampled cgroup pressure/OOM events; `tj` ranged from
48.5 to 57.2 °C. It observed GPU 306 MHz–1.300 GHz and CPU 730 MHz–2.202 GHz
under dynamic policy; EMC readback was unavailable. Rail readings were not
attributed as request energy.

The initial attempt to place the screen inside `run_control.py` was stopped by
the harness's shared board lock before any model cell launched. That failed
wrapper attempt is retained under `screen/` and `screen-supervisor/` and
excluded. The corrected one-block feasibility screen is `screen-run1/`; the
seven confirmation blocks are `block-01/` through `block-07/`.

The workload SHA256 is
`c80ade67777ad08470fb9bd61ffa75d294af64e7958af6e9e25792103970b9e7` and the
candidate service SHA256 is
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`.
`config.json`, `workload.json`, and `artifacts.json` pin the run configuration, workload, model, packs, tokenizer, and candidate binary identity. Reproduce from the repository root under the same 28-GiB ceiling with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G \
  bench/results/2026-10-15-phase6-q2-prefill-cache-fixedslots/run_confirm7.sh
python3 bench/results/2026-10-15-phase6-q2-prefill-cache-fixedslots/analyze.py
systemd-run --user --scope --collect -p MemoryMax=28G \
  bench/results/2026-10-15-phase6-q2-prefill-cache-fixedslots/run_clock_confirm7.sh
python3 bench/results/2026-10-15-phase6-q2-prefill-cache-fixedslots/analyze_clock_confirm7.py
```

`SHA256SUMS.txt` covers the retained run inputs, raw cell outputs, telemetry,
and analysis. No default changed; Phase 6 remains open for its other workload
and interaction gates.

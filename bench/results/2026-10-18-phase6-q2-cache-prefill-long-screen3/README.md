# Q2_0 long-retrieval cache × prefill screen — Orin — 2026-10-18

This three-block randomized screen crossed exact expert cache capacities of
3,000 and 3,500 slots with prefill chunks of 32 and 128 on a 7,501-token
retrieval prompt. It used Q2_0, FP16 KV, MTP off, 8,192 context, eight workers,
disabled prompt cache and adaptive swaps off. Each of the 12 cells ran one
measured request in a fresh service, after a separate 512-token warmup, under a
28-GiB cgroup cap and six-GiB admission/headroom floor.

All 12 cells passed with the exact three-marker response, 7,501 prompt tokens
and 36 completion tokens. The independent analyzer verified the configured
cache capacity matched actual slots in every cell. Across 6,169 memory samples,
minimum host availability was 17.42 GiB and minimum effective admission
availability was 10.59 GiB. Cgroup low/high/max/OOM/OOM-kill counters remained
zero. GPU clock observations ranged 306 MHz–1,300.5 MHz; CPU observations ranged
729.6 MHz–2,201.6 MHz; EMC readback was unsupported. `tj` ranged 45.94–55.81 °C.
Clocks remained dynamic; request-attributed energy was not measured.

| Cache slots | Chunk | Median request time | Median prompt rate |
| ---: | ---: | ---: | ---: |
| 3,000 | 32 | 669.3 s | 11.3 tok/s |
| 3,000 | 128 | 270.3 s | 28.3 tok/s |
| 3,500 | 32 | 689.2 s | 11.0 tok/s |
| 3,500 | 128 | 266.1 s | 28.7 tok/s |

Chunk 128 reduced median request time by 59.56% at 3,000 slots and 61.38% at
3,500 slots. The cache × chunk interaction estimate (chunk effect at 3,500
minus chunk effect at 3,000) was −2.93 percentage points, with a three-block
paired bootstrap interval of −3.79 to −1.75 points. The cache-size effect was
uncertain at chunk 32 (+2.97%, interval −1.54% to +7.92%) and favored 3,500 at
chunk 128 (−2.18%, interval −8.24% to −1.49%). These three-block intervals are
screening estimates with few resampling units. Treat the interaction as a
candidate for confirmation, not a settled effect or a profile promotion.

A distinct held-out prompt is being used for a seven-block confirmation. Its
results will be recorded separately. No default or selected serving profile
changed from this screen.

The full cell timings and paired effects are in `analysis.json`; per-cell
request output, server configuration, supervisor record and compressed memory
and tegrastats logs are retained. `artifacts.json`, model shard hashes and
binary identity pin the test inputs. Reproduce the screen from the repository
root with `run_screen3.sh`, then run `python3 analyze_screen.py`.

# CPU expert-pool worker screen — Orin — 2026-10-10

This randomized 3-block screen compared 1, 2, 4, 8 and 11 CPU expert-pool
workers on the same IQ1_M candidate, exact 512-token prompt and 64-token greedy
request. Every process received a distinct 512-token warmup prompt first; the
measured request therefore passed the fresh-prefill check (`cache_n=0`). Actual
expert cache capacity was 6,519 slots in every cell. The run retained request
streams, engine logs, state fingerprints, memory samples and raw tegrastats.
The supervisor's minimum physical availability was 8.29 GiB, above the 6 GiB
floor.

| Workers | Median request (ms) | Median prefill (ms) | Median decode (ms) |
| ---: | ---: | ---: | ---: |
| 1 | 15,734.3 | 11,991.0 | 3,743.3 |
| 2 | 14,410.0 | 10,843.5 | 3,566.5 |
| 4 | 13,062.2 | 9,691.1 | 3,371.1 |
| 8 | 12,081.6 | 8,729.1 | 3,307.0 |
| 11 | 12,763.2 | 9,287.2 | 3,476.0 |

Relative to 11 workers, paired request-time median deltas were +21.73% for 1
(95% paired-bootstrap interval +21.15% to +25.13%), +13.64% for 2 (+12.90% to
+17.07%), +3.83% for 4 (−0.42% to +3.88%), and −3.92% for 8 (−8.43% to
−2.66%). These are exploratory timings only: the correctness gate failed.
One of three 11-worker requests produced a different output hash, and the
measured persistent-state fingerprints differed across all worker settings.
The remaining 14 output hashes matched. Because this prevents a clean
worker-count comparison, no speedup is claimed and no default is changed.

The output difference occurred with temperature zero. The run therefore needs
follow-up to determine whether speculative generation, CPU/GPU scheduling or
another source of execution nondeterminism caused it. Future comparisons should
capture deterministic token IDs and accepted-prefix state at each verifier
commit before using worker-count timing as a tuning result. State fingerprints
are retained as evidence; their mismatch is not explained away by matching
final text.

The initial attempt at `../2026-10-10-phase4-pool-workers-512/` is preserved as
a failed harness setup: warmup reused the measured prompt and violated the
fresh-prefill gate. The corrected distinct-warmup path was separately smoke
tested at `../2026-10-10-phase4-pool-workers-warmup-smoke/`. The helper adds an
optional `--warmup-workloads` input to the API benchmark harness; default
workloads and normal invocation behavior are unchanged.

# Prefetch fill versus staging confirmation — Orin — 2026-10-10

This seven-pair confirmation compares `STRATA_IO_PF_STAGE=0` (predicted
whole-blob reads populate the OS page cache) with `STRATA_IO_PF_STAGE=1` (the
same read-ahead path hands predicted blobs from pageable host staging buffers).
Both arms use whole-blob prefetch, so this isolates the staging choice. The
IQ1_M validation cohort, formatted 512-token prompt
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`, 64 output
tokens, requested 3,000 expert slots (3,903 actual), context 8,192, candidate
binary `d3e8bcde3a430d7d5bb614fec8ba938398699b9abecd41965bb28fd6d465d721`, and
all other engine arguments were held fixed. Pair order was randomized with
seed 20261014. All 14 arms returned the same 64 token IDs, all nine persistent
state fingerprints, and the same actual cache capacity. The six-GiB
supervisor recorded minimum physical `MemAvailable` of 14,071,853,056 bytes
(13.11 GiB).

| Pair | Order | Fill request ms | Stage request ms | Paired delta | Fill scoped reads GB | Stage scoped reads GB | Stage blobs used | Decode wait ms |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | stage / fill | 34,091.7 | 32,109.8 | −5.81% | 10.671 | 9.324 | 205 | 1,143.7 |
| 1 | stage / fill | 33,511.7 | 33,161.2 | −1.05% | 10.303 | 9.930 | 325 | 1,494.6 |
| 2 | fill / stage | 33,926.7 | 32,871.9 | −3.11% | 10.671 | 10.164 | 296 | 1,565.5 |
| 3 | fill / stage | 33,975.6 | 33,612.0 | −1.07% | 10.948 | 10.633 | 260 | 1,443.9 |
| 4 | fill / stage | 33,520.7 | 32,411.4 | −3.31% | 10.196 | 9.554 | 290 | 1,627.3 |
| 5 | fill / stage | 63,170.5 | 32,466.0 | −48.61% | 10.017 | 9.545 | 312 | 1,698.9 |
| 6 | fill / stage | 32,471.6 | 35,169.0 | +8.31% | 9.548 | 10.121 | 274 | 3,395.9 |

The paired median request-time delta was −3.11%; a 200,000-draw bootstrap of
the paired median (seed 1014, resampling whole pairs) gave −5.81% to −1.05%.
Median request time was 33,926.7 ms for fill and 32,871.9 ms for stage. Median
scoped read bytes were 10.303 GB and 9.930 GB respectively; the median paired
stage-minus-fill read delta was −0.472 GB. Every fill arm reported zero staged
blobs consumed and zero decode-wait fetches. Staged arms consumed 205–325
prefetched blobs and reported 1,143.7–3,395.9 ms aggregate wait across 1,292–
1,729 fetches. Owner traces observed a pageable host staging allocation peak
of 175,718,400 bytes (167.6 MiB) in one stage arm; fill arms had no staging
allocation. The engine therefore takes staged buffers in real requests, but
the measured wait also shows that read-ahead does not always finish before
consumption.

The result supports a workload-specific screening benefit, not promotion: one
fill arm took 63.2 seconds versus its 32.5-second stage pair, and one stage arm
was 8.31% slower than its paired fill arm. Clocks were dynamic and EMC/GPU
frequency samples were unavailable. Rail integrals are system-wide and not
process energy. This confirmation uses one prompt, cache point and model; a
held-out prompt/context and the requested user-facing energy/memory tradeoff
are still needed for a general decision. The feature remains opt-in and no
default changed.

The complete raw arm logs, state fingerprints, owner observations, scoped
`io.stat` deltas, tegrastats and supervisor telemetry are retained under
`experiment/` and `supervisor/`. The matching three-pair screen is recorded in
the [screening report](../2026-10-10-phase3-transfer-stage-screen/README.md).

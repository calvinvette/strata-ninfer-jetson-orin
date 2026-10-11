# Trace-free pageable versus pinned stage timing — Orin — 2026-10-11

This seven-pair randomized screen separates timing from the earlier traced
pageable/pinned correctness run. It uses `STRATA_STAGE_PIN=0/1` to select the
pageable/pinned expert-stage host buffers, with the same Qwen3.8-Flash-Next
Coder IQ1_M model, MTP weights, tokenizer, 512-token prompt, 64-token generation,
requested 3,000-MiB expert cache, one pool worker, and spec4 in every arm. The
six-GiB supervisor passed; minimum host `MemAvailable` was 14,138,507,264 bytes
(13.17 GiB). Both arms admitted 3,903 cache slots, observed 39,660 hits out of
56,160 lookups, and emitted 64 tokens. All seven paired token-ID sequences
matched.

This uses engine prompt/decode stage times without the API server. State hashes,
owner events and `STRATA_TRACE` were disabled to avoid tracing overhead; it does
not claim persistent-state parity. The earlier [three-pair traced check](../2026-10-11-phase3-stage-pin-confirm512/README.md)
matched all nine state fields and confirmed both staging owner classes, but its
timings were trace-contaminated. Do not merge the correctness and timing arms
into one measurement.

| Engine stage | Pageable median | Pinned median | Paired pinned/pageable median delta (95% bootstrap interval) |
| --- | ---: | ---: | ---: |
| Prompt | 13,930.7 ms | 13,997.7 ms | +0.48% (−3.64%, +10.45%) |
| Decode | 11,455.2 ms | 14,014.7 ms | −2.13% (−46.18%, +134.52%) |
| Prompt + decode stage sum | 26,037.0 ms | 27,942.0 ms | +12.10% (−24.00%, +58.19%) |

Paired effects are the median of seven within-pair pinned/pageable ratios minus
one; intervals resample complete pairs 100,000 times with deterministic seeds.
The point estimates and broad intervals do not establish an end-to-end benefit
for pinned staging. No mode or default is promoted. Dynamic CPU clocks ranged
from 729 to 2,201 MHz in tegrastats; GPU and EMC clock values were unavailable.
This was one prompt/cache/configuration screen, not a held-out confirmation or
thermal-equilibrium run. Whole-device energy and physical disk-byte deltas are
not attributed per arm.

The engine's per-request expert-file counters were similar between arms: median
engine-reported file-tier expert reads were 39,781.0 MB pageable and 39,793.8 MB
pinned; median pread bytes were 3,147.0 and 2,897.4 MB, respectively. Median summed prefetch
worker time was 5,592.2 ms pageable and 4,028.8 ms pinned, while median decode
wait was 1,154.3 and 1,086.6 ms. These are engine counters; pread/readahead and
whole-device reads do not identify physical bytes uniquely consumed by one
request. Pageable/pinned requested backing was measured separately in the
traced correctness report.

The runner's `--timing-only` mode removes inherited state, integration-owner and
engine trace flags while retaining token-ID checks. It now computes paired
median ratios and bootstrap intervals from full process-pair samples. The
recorded `experiment/results.json`, per-arm logs and `artifact-identities.json`
contain the inputs and raw counters; supervisor memory samples and tegrastats
are retained beside them. Model and pack files remain under `~/models/`.

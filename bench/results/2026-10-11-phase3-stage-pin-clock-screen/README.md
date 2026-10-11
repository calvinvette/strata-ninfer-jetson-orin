# Pageable versus pinned staging clocked screen — Orin

Run date: 2026-10-11 on local `orin1` (Orin AGX, ARM64, CUDA 12.6). This
three-pair randomized timing screen used the Coder IQ1_M model with MTP,
3,000 requested cache slots (3,903 actual), context 8,192, prefill chunk 512,
spec4, 512 prompt tokens and 64 generated tokens. Both arms enabled file-tier
prefetch and staging; only `STRATA_STAGE_PIN` changed. The trace-free timing
mode intentionally did not collect persistent-state hashes.

All six arms completed and each pair returned identical token IDs, the same
cache residency and the same cache hit/lookup counts. Pageable/pinned prompt
medians were 14,472.0/14,000.2 ms; the paired pinned-minus-pageable median
delta was −2.38% (95% paired bootstrap interval −11.50% to +1.65%). Decode
medians were 11,783.7/16,696.5 ms; the paired median delta was +43.65%
(interval −3.78% to +80.34%). Total request delta was +18.12% (interval
−8.12% to +37.93%). The three-pair interval spans zero in all measures and
the decode timings are highly variable. This does not establish a benefit or
justify changing the default.

The supervisor passed with minimum host `MemAvailable` of 14,238,662,656 bytes
(13.26 GiB), above the six-GiB floor. Read-only clock samples were aligned to
each arm's monotonic start/end timestamps. GPU observations ranged from 306 to
1,300.5 MHz in every arm; per-arm medians were 306, 408, 306, 510, 306 and 408
MHz in run order (pageable/pinned for pairs 0–2). EMC stayed at 3,199 MHz.
Sampled CPU frequencies ranged from 729.6 to 2,201.6 MHz in every arm. These
are sampled dynamic rates, not controlled or sustained clocks. Clock readings
do not explain or correct the observed variance. Energy was not measured; raw
tegrastats are retained.

The arm timing markers were added to `stage_buffer_parity.py` so supervisor
samples can be joined to individual process arms. The exact arguments, model
paths, prompt hash, binary hash and per-arm metrics are in
`experiment/results.json`; raw clock/memory samples and process logs are in
`supervisor/` and `experiment/`. The integration Python suite passed 99/99.
Models remain under `/home/calvin/models/`; no model or build products are
included.

This is a timing-only screen, not persistent-state evidence. Earlier pinned
stage checks cover state parity and a held-out 2,048-token timing cell. Together
these do not close Phase 3's wider memory-pressure, unique-backing,
transfer-latency or admission gates. Pageable staging remains the default.

# Q2_0 pageable versus pinned expert staging, 2,048/64 screen — Orin

Date: 2026-10-11 on orin1 (Orin AGX, CUDA 12.6). The Q2_0 validation model
used the current candidate binary
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`. Both
arms used 256 requested expert-cache slots, 8,192 configured context, spec2,
prefill chunk 512, 2,048 actual prompt tokens, 64 generated tokens, and a
distinct 172/64 warmup. Only `STRATA_STAGE_PIN` changed within each pair.

The separate trace-enabled [correctness/owner screen](../2026-10-11-phase3-q2-stage-pin-correctness2048/experiment/results.json)
passed all three randomized pairs. Generated IDs and all nine persistent-state
fields matched; pageable and pinned stage owners each reported 353,894,400
requested bytes. Orders included one pinned-first pair and two pageable-first
pairs. Its supervisor passed with minimum `MemAvailable` of 22,778,261,504
bytes.

The separate trace-free [timing screen](../2026-10-11-phase3-q2-stage-pin-timing2048/experiment/results.json)
also passed all three pairs' token-ID comparisons. Paired pinned-minus-pageable
median deltas were +1.48% for prompt time, −3.30% for decode, and +3.25% for
engine request time. The corresponding 95% bootstrap intervals were −0.73% to
+127.19%, −53.50% to +6.62%, and −1.67% to +31.58%. One pinned prompt-time
sample was 53,090 ms while the other two were about 23.5 seconds, making this
small screen highly uncertain. Pageable/pinned per-arm medians were 23,368.5/
23,527.7 ms prompt, 13,651.5/12,910.8 ms decode, and 37,351.9/36,729.1 ms
request (median of per-arm prompt plus decode). The timing supervisor passed
with minimum `MemAvailable` of 22,764,007,424 bytes.

Each supervisor retained read-only clock samples: CPU 729.6–2,201.6 MHz, GPU
306–1,300.5 MHz, and EMC 3,199 MHz. The timing result is a three-pair screen,
not a confirmation; intervals span zero, clocks were dynamic, and energy was
not measured. Together with the separate 512/64 screen, this does not establish
a staging benefit across workloads. Pageable staging remains the default.

Raw correctness/owner data and supervisor records are in
`../2026-10-11-phase3-q2-stage-pin-correctness2048/`; raw timing and supervisor
records are in `../2026-10-11-phase3-q2-stage-pin-timing2048/`. Models and build
products remain outside Git under `/home/calvin/models/` and `build/`.

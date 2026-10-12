# Q2_0 pageable versus pinned expert staging, 512/64 timing screen — Orin

Date: 2026-10-11. This trace-free screen compared pageable and pinned expert
staging using the Q2_0 validation model on orin1 (Orin AGX, CUDA 12.6). The
candidate executable SHA256 was
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`. Both
arms used file-tier prefetch/staging, MTP batch 1, speculation 2, 256 requested
expert-cache slots, 8,192 configured context, 512-token prefill, and 64 output
tokens. Each process first ran a distinct 172/64 warmup. Only
`STRATA_STAGE_PIN` changed within each pair.

Six randomized process pairs were collected in two supervised three-pair
blocks. The first block placed pinned first in all three pairs; the second
block placed pageable first twice and pinned first once. All six pairs returned
identical token IDs. The combined paired pinned-minus-pageable median deltas
were −9.41% for prompt time, −4.31% for decode time, and −6.81% for engine
request time (prompt plus decode). Paired 95% bootstrap intervals were
−18.74% to +31.50%, −7.68% to +7.62%, and −12.26% to +17.02%, respectively.
Per-arm medians were 8,271.95/8,155.95 ms prompt, 12,013.4/11,753.1 ms decode,
and 20,285.35/19,907.35 ms request (pageable/pinned). The wide intervals span
zero; this screen does not establish a product benefit. It reports engine
prompt/decode timing, not client TTFT.

The first block's supervisor passed with a minimum `MemAvailable` of
22,429,360,128 bytes; the order-balanced block passed with 22,645,743,616
bytes. Both remained above the six-GiB floor. Each recorded 339 memory/clock
samples; sampled CPU rates ranged 729.6–2,201.6 MHz, GPU rates 306–1,300.5 MHz,
and EMC stayed at 3,199 MHz. These were dynamic read-only observations. Energy
was not measured. The paired variability and order imbalance in the first block
remain visible rather than being adjusted away.

The matching trace-enabled Q2_0 [three-pair state and owner check](../2026-10-11-phase3-q2-stage-pin-warmup-state3-rerun3-nocap/README.md)
passed warmup completion, measured token IDs, all nine persistent-state fields,
and observed pageable/pinned stage owners with 353,894,400 requested bytes per
arm. That separate run supplies correctness/ownership evidence; timing from it
is excluded here because tracing was enabled. Combining the two measurements
supports a bounded screening observation for this single configuration only.
Pageable staging remains the default pending a held-out workload and broader
memory, fault, disk, and energy assessment.

Raw experiment arms are in `../2026-10-11-phase3-q2-stage-pin-timing512-current/`
and `../2026-10-11-phase3-q2-stage-pin-timing512-order-balance/`; each retains
the result JSON, supervisor telemetry, and raw tegrastats. The downloaded model
and build products remain outside Git under `/home/calvin/models/` and
`build/`.

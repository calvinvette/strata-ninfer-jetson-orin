# Pageable versus pinned staging at 2,048 prompt tokens — Orin

Run date: 2026-10-11 on the local `orin1` Orin AGX (ARM64, CUDA 12.6). This
held-out prompt-length timing confirmation used the Coder IQ1_M model with MTP,
3,000 requested cache slots (3,903 actual slots), context 8,192, prefill chunk
512, spec4, 2,048 formatted prompt tokens and 64 generated tokens. Seven
randomized process pairs changed only `STRATA_STAGE_PIN`; file-tier prefetch and
staging were enabled in both arms. The timing-only mode disabled owner and
persistent-state trace instrumentation.

All 14 arms completed and every pair returned identical 64 generated token
IDs, the same 3,903-slot cache and 39,649 hits / 56,160 lookups. This campaign
did not hash persistent state, so state parity is not claimed. The exact prompt
SHA256, engine SHA256, model artifact identities, arguments and arm data are
recorded in `artifact-identities.json`, `config.json` and
`experiment/results.json`.

Pageable median prompt time was 22,921.8 ms and pinned was 23,474.8 ms. The
paired pinned-minus-pageable prompt delta was +0.19% (95% paired bootstrap
interval −0.99% to +3.14%). Pageable median decode time was 13,109.1 ms and
pinned was 11,215.8 ms; paired median delta was −6.52% (interval −40.20% to
−0.26%). Total request median paired delta was −0.18% (interval −18.49% to
+1.48%). Decode and total request results are highly variable and the total
interval includes zero. These timings do not establish an end-to-end benefit;
pinned staging remains opt-in. This result does not measure staging allocation
size, copy latency, or energy.

The six-GiB supervisor completed successfully with minimum physical
`MemAvailable` of 13,985,615,872 bytes (13.02 GiB); no cgroup memory events
reported pressure or OOM. Power mode and clocks were not independently sampled
for this run. Raw tegrastats rails are retained but are not an integrated
energy measurement. Supervisor telemetry is retained under `supervisor/`; per-arm logs are in
`experiment/`. Models remain under `/home/calvin/models/`; no model or build
products are included.

This held-out prompt-length cell adds timing evidence to the earlier 512-token
pinned-stage correctness and timing screens. It does not close Phase 3's wider
memory-pressure, unique-backing, transfer-latency or admission gates and does
not change any default.

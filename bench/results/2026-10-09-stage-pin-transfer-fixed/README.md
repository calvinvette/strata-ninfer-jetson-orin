# Pinned versus pageable expert staging — Orin

Run date: 2026-10-09 on the local `orin1` Orin AGX, ARM64, CUDA 12.6. The same
candidate binary and Coder IQ1_M model artifacts were used in all arms. The
formatted prompt was exactly 4,096 tokens and generation was capped at 64 tokens.
All arms requested a 5,000-slot expert cache and reported 6,519 actual slots,
context 8,192, prefill chunk 64 and spec4/MTP. File-tier prefetch and staging
were explicitly enabled in both modes with `STRATA_IO_PREFETCH=1` and
`STRATA_IO_PF_STAGE=1`; only `STRATA_STAGE_PIN` changed. The order was randomized
for three process pairs (pinned/pageable, pinned/pageable, pageable/pinned).

All three pairs emitted identical token IDs and matched all nine recorded
persistent state fields. Both observed owner classes were released in every
completed arm. Median engine prefill time was 99,103.8 ms pageable and
99,640.5 ms pinned (+0.54%); median decode time was 5,293.6 ms pageable and
5,821.1 ms pinned (+9.96%). Median requested expert-stage host backing was
109,158,400 bytes pageable and 138,444,800 bytes pinned. File-read counters and
per-arm timings vary in the raw results; copy latency and energy were not
measured separately. These three screening pairs show no product benefit for
pinned staging on this workload, so pinned staging remains opt-in and is not
promoted. This does not establish behavior for other prompts, cache capacities,
formats or hardware.

The two supervisor windows both enforced the 6 GiB floor. Minimum
`MemAvailable` across the combined experiment was 8,723,185,664 bytes (8.12
GiB); the resumed window alone reached a minimum of 8,856,866,816 bytes (8.25
GiB). Energy was not measured. The experiment process used separate engines
sequentially; no model or build artifacts are stored here.

The initial supervisor completed pair 0 but the then-current runner raised a
Python error while recording its comparison (`order` entries were tuples). The
raw result already contained both arms. A subsequent supervisor resumed from
that durable pair, verified it, and completed pairs 1 and 2; both supervisor
windows and the full six-arm result are retained. Two earlier exploratory runs
are retained separately: one disabled state hashing by setting prompt-cache to
zero, and another enabled page-cache prefetch without staging. They did not
exercise a valid staging comparison and are not included in the three-pair
summary.

The engine binary SHA-256 is recorded per arm in `experiment/results.json`.
Native and maestro1 HIP source/build identities are in this report's `native/`
directory. This is local Orin CUDA
runtime evidence plus x86 HIP compile evidence; maestro1 supplies no AMD GPU
runtime result. Verify report files using the adjacent `SHA256SUMS` manifests.

After fixing the trace deleter to report pinned frees only after successful
`cudaFreeHost`, the rebuilt native binary passed a separate 512-token/8-output
pair. Both modes matched output and state; their stage owner events had zero
live bytes at teardown. That run's owner logs and six-GiB-supervised telemetry
are under `trace-lifecycle-check/`.

# Q2_0 prefetch fill versus staging — Orin — 2026-10-11

This three-pair screen compared the file-tier read-ahead modes
`STRATA_IO_PF_STAGE=0` (read predicted blobs to page-cache scratch) and `=1`
(stage predicted blobs in pageable host buffers) using the Q2_0 validation
model. Both arms enabled the same prefetch worker path. They used 256 requested
and actual expert-cache slots, 8,192 configured context, spec2, 512 prompt
tokens, and 64 generated tokens. Pair order was randomized (stage/fill, then
fill/stage, fill/stage). The candidate binary SHA256 was
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.

All pairs matched output IDs, all nine persistent-state fields, and actual
cache capacity. The paired stage-minus-fill request-time deltas were −5.08%,
+3.84%, and −1.88%; the median was −1.88%, with a three-pair whole-block
bootstrap 95% interval of −5.08% to +3.84%. Per-arm median request times were
28,939.3 ms for fill and 28,417.9 ms for stage. This is a small screen with a
wide interval spanning zero, so it does not establish an end-to-end benefit.

Each arm's engine trace reported about 53.8–54.9 GB of logical expert reads.
The process `read_bytes` and cgroup-scoped I/O counters were unavailable in
this run. Host block-device reads were measurable on `nvme0n1p1`, but those
counter deltas include unrelated device reads and kernel readahead: median
4,584,423,424 bytes for fill and 6,466,830,336 bytes for stage. Major-fault
medians were 1,202 and 1,626; minor-fault medians were 588,140 and 595,401.
These measurements do not isolate model-file bytes or prove that staging
caused the whole-device delta.

The owner trace observed an `expert-stage-pageable-host` peak of 353,894,400
requested bytes in both modes, with zero live requested bytes at teardown. This
indicates the allocation exists in both arms even though the read-ahead data
path changes; it is requested payload accounting, not separate physical
backing. Staged arms reported 477–958 prefetch blobs used and 9.54–10.29
seconds of aggregate fetch wait; fill arms reported 313–557 used and 9.90–10.46
seconds of wait. Prefetch counters and wait are descriptive engine sums, not
wall-clock time that can be added to the request.

The six-GiB supervisor passed with minimum host `MemAvailable` of
22,858,883,072 bytes. It collected 2,103 tegrastats samples; named rail energy
and clocks are system-wide and include unrelated activity, so they are not
reported as process energy or used to rank the modes. The first invocation
failed before engine startup because the original harness expected
`pack/experts.bin`, which this native Q2_0 pack does not contain. It is retained
at [`../2026-10-11-phase3-q2-prefetch-stage-screen/`](../2026-10-11-phase3-q2-prefetch-stage-screen/).
The harness now accepts an explicit artifact path for device-wide block
counters; the Q2_0 first GGUF shard identified the filesystem in this run.

Raw per-arm state, ownership, fault, host block-device and tegrastats records
are in `experiment/`; supervisor memory and clock samples are in
`supervisor/`. The result is specific to this model, prompt, cache and device.
It does not promote either read-ahead policy or close Phase 3's broader
pressure, unique-backing, transfer-latency and energy gates.

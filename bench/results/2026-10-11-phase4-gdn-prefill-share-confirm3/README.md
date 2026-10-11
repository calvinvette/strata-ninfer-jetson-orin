# Three-process CPU prefill-share-disabled confirmation — Orin — 2026-10-11

This repeats the same 512-token/eight-output IQ1_M accepted-prefix diagnostic
with eight expert-pool workers, 6,519 actual cache slots, MTP enabled and
`STRATA_PREFILL_CPU_SHARE=0`. Three independent server processes ran after
distinct 512-token warmups. Full state fingerprints and full-width hashes for
all 36 GDN state slices were captured at each verifier commit.

All three measured requests completed above the six-GiB floor. Minimum sampled
`MemAvailable` was 9,052,065,792 bytes (8.43 GiB). Each emitted the same eight
token IDs and output-text hash; full accepted-prefix traces, aggregate state
fingerprints and all 36 per-GDN hashes matched exactly. The experiment result
is `passed=true` with no failures. Raw server configs, requests, engine logs and
supervisor telemetry are retained in this folder.

Together with the earlier [two-process control](../2026-10-11-phase4-gdn-prefill-share-control/README.md),
this makes five no-share process repetitions across two independent runs. It
strengthens the finding that the default CPU/GPU prefill split is associated
with the observed same-worker state drift. It does not qualify answer quality
or show whether disabling CPU share is a good serving policy. No latency result
is used because the per-commit tracing path synchronizes and copies state.

Model artifacts remain in `~/models/`; their checksums are in
`model-artifact-identities.json`.

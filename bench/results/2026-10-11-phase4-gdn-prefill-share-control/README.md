# CPU prefill-share determinism control — Orin — 2026-10-11

This control repeats the same two-process, 512-token/eight-output IQ1_M
correctness diagnostic as the [full-width GDN localization run](../2026-10-11-phase4-gdn-layer-fullhash/README.md),
with eight expert-pool workers and 6,519 actual cache slots. The only runtime
setting changed was `STRATA_PREFILL_CPU_SHARE=0`; model, weights, MTP, context,
prompt, cache and worker count were held fixed. The opt-in full state and
per-GDN hashes remained enabled.

Both requests completed under the six-GiB supervisor. Minimum `MemAvailable`
was 9,096,773,632 bytes (8.47 GiB). The two runs emitted the same eight token
IDs and output hash. Their L=512 first-prefix state fingerprints matched, all
accepted-prefix traces were identical, and all 36 full-width per-GDN hashes
matched. The experiment screen reports `passed=true`; raw requests, engine
logs, supervisor telemetry and exact config/workload copies are in this
folder.

This supports CPU prefill sharing as the source of the drift observed with the
default setting. It does not show that turning sharing off improves quality,
latency, throughput, energy or memory, and it does not qualify the default
path. A [three-process confirmation](../2026-10-11-phase4-gdn-prefill-share-confirm3/README.md) then reproduced exact output and state across three additional processes, matching all 36 per-GDN hashes. This strengthens the correctness observation to five no-share processes across two runs. An explicit quality/performance comparison remains required before any policy decision.

The model artifacts remain in `~/models/`; checksums are recorded in
`model-artifact-identities.json`.

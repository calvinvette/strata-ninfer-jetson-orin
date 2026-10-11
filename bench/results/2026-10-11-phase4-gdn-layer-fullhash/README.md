# Full-width GDN state localization — Orin — 2026-10-11

Two independent IQ1_M API processes used the same 512-token prompt, eight-token
output limit, 6,519-slot expert cache, MTP configuration and eight-worker pool.
The opt-in `STRATA_STATE_HASH_GDN=1` diagnostic now emits full 64-bit FNV-1a
hashes for each of the 36 GDN state slices. All generated tokens completed
above the six-GiB supervisor floor (minimum `MemAvailable` 8.48 GiB).

With default CPU prefill sharing enabled, the processes matched on the first
three GDN state slices at the L=512 committed prefix and first diverged at GDN
ordinal 3. The model uses QSA every fourth layer (`qsa_interval=4`), so ordinal
3 is the GDN state after the first QSA layer. The two runs had identical first
six generated token IDs but differed on token seven and produced different
output text hashes. Full accepted-prefix records and 36 per-slice fingerprints
are in `experiment/`; parsed comparisons are in `analysis.json`.

A companion [CPU-share-disabled control](../2026-10-11-phase4-gdn-prefill-share-control/README.md)
used the same candidate, prompt, model artifacts, cache, MTP and worker count
with `STRATA_PREFILL_CPU_SHARE=0`. Its two processes matched all eight token
IDs, all accepted-prefix state fingerprints and all 36 GDN slice hashes. This
controlled result supports the CPU/GPU split of prefill expert work as the
source of repeat-to-repeat drift. It is a two-process correctness screen, not
a completed root-cause audit, quality qualification, or performance comparison.
No worker timing is qualified and no default is changed.

The native CUDA `strata` target built and `--help` exited 0. The changed shared
CUDA/HIP generator compiled in the maestro1 HIP build, and HIP `--help` exited
0. SYCL uses a separate generator source, so it is unaffected by this change.
The opt-in diagnostic is unset on normal runs. Source and binary identities,
HIP logs, configurations, workload identity, model artifact checksums, traces
and supervisor telemetry are retained here. The model artifacts remain in
`~/models/`.

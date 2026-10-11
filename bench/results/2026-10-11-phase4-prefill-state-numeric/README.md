# Prefill-chunk GDN state difference — Orin — 2026-10-11

This follow-up quantifies the first accepted-prefix GDN difference observed in
[the chunk trace](../2026-10-11-phase4-prefill-state-trace/README.md). It uses
the same 1,069-token held-out formatted prompt, eight-token generation cap,
Coder IQ1_M model, Q2_0 MTP runtime, one pool worker, disabled CPU prefill
sharing, 4,096 context, 5,000 cache budget and prompt cache 6. Each process had
a distinct 172-token warmup, so the opt-in state dump only fired at measured
`L=1069`, immediately after output token ID 32 was committed. Both requests
completed eight tokens and the API reported 1,069 prompt tokens. No performance
comparison is inferred from these instrumented runs.

The two dumps each contain 36 × 817,152 float32 values (117,669,920 bytes
including the 32-byte header). Compared with chunk 32, chunk 128 differs in
28,938,102 values (98.37%). The global RMS absolute difference is 0.008446 and
the relative L2 norm is 3.138%. Per-layer relative L2 ranges from `6.97e-7`
(layer 0) to `5.33e-2` (layer 27); the largest single absolute difference is
2.028 in layer 33. Exact per-layer values and dump SHA256s are in
[`analysis.json`](analysis.json) and [`SHA256SUMS`](SHA256SUMS).
Both the native CUDA rebuild and the maestro1 HIP build passed; the exact
commands and executable hashes are in [`backend-build.txt`](backend-build.txt).

Both runs remained above the required six-GiB host-availability floor: minimum
`MemAvailable` was 8.48 GiB for chunk 32 and 8.45 GiB for chunk 128. The prior
four-run trace matched all token IDs and repeated the same per-layer state hash
within each chunk setting. This new one-run-per-setting numeric comparison shows
that the difference is materially larger than a bitwise rounding discrepancy.
It does not establish which state is more accurate or whether either difference
changes quality on a task. Prefill chunk remains unqualified; no default is
promoted.

The debug dump is opt-in via `STRATA_STATE_DUMP_GDN` and
`STRATA_STATE_DUMP_GDN_AT`. With either unset the new branch is inactive. The
compiled candidate SHA256 is recorded in the local run configs and logs. Raw
117.7 MB state dumps, model files and engine logs stay on the Orin; their checksums
and compact derived analysis are retained here. The failed initial launch caused
by using system Python without `jinja2` is preserved in
`chunk32-supervisor/`; the successful retry used
`~/models/strata-orin-validation/pack-venv/bin/python`.

# Elastic KV growth with cache-matched MTP state

This correctness-only diagnostic compared Q6 IQ1_M MTP-off and MTP4 on the
same exact synthetic 9,000-token prompt at a 16K context, FP16 KV and 32 output
tokens. Both used `--expert-cache 2993`, a 2,048-cell initial KV, 2,048-cell
growth steps, Q6 warp dequant, and the same binary, model files and prompt hash
(`665348b6a0c94e898deec18f516d78b7aa0162c5c13ee691506555f7d8f5779a`). The
accepted-prefix oracle disabled adaptive swaps so it could isolate MTP and the
KV-growth residency changes. It captured token IDs and all nine persistent
state fields at each shared commit boundary. Both arms used candidate binary
SHA256 `857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`;
the pinned model, MTP assets and tokenizer hashes are retained in
`model-identity.json`.

## Default growth floor: mismatch reproduced

Both services started with 3,895 expert slots. At the first prompt growth to
10,240 KV cells, MTP-off gave 102 slots to KV and retained 3,793 resident
experts; MTP4 gave 109 and retained 3,786. Token IDs still matched across the
two 32-token outputs, but GDN, PLE, tail, pooled, pooled-full and KV state
differed at every shared accepted-prefix boundary and at request end. The
result is a correctness failure, not a process or memory failure. Minimum host
availability was 13.42 GiB; the six-GiB floor remained intact.

## Matched growth floor: state parity restored

The follow-up set `STRATA_KV_GROW_FLOOR=3793`. Both arms then retained exactly
3,793 expert slots while growing to 10,240 KV cells. MTP-off used the 102
chunks relinquished from the cache. MTP4 relinquished the same 102 and mapped
additional fresh VRAM for its larger KV requirement. The arms matched all 32
token IDs, all nine final state fields, and all 15 shared accepted-prefix
boundaries (1, 3, 5, 8, 9, 12, 15, 17, 21, 25, 27, 28, 29, 30, 32). MTP4
offered/accepted 42/17 drafts. Minimum host and effective admission availability
was 13.30 GiB; cgroup OOM and limit counters stayed zero.

This supports differing resident cache capacity during growth as the cause of
the reproduced MTP state mismatch for this exact prompt and configuration. It
does not prove a general causal rule, validate the default floor for other
contexts, or qualify output quality/performance. The passing policy consumes
additional fresh VRAM when MTP4 needs it. The default floor is unchanged, and
the lower-floor growth path remains unqualified for MTP parity.

The first launch was rejected before model startup because the test helper
disables swaps while the inherited config enabled `--adapt-accepted-only`; it
is retained under `trace/`. The no-floor run and the floor-controlled pass are
under `trace-rerun/` and `trace-floor3793/`. Their supervisor telemetry and
startup refusal are retained alongside the raw state traces. Models remain in
`~/models/`.

# GDN per-token state capture attempt — unsupported T=2 window — Orin — 2026-10-20

This supervised adaptive-cap-8 service run selected layer-26 pre/post GDN state
at prompt positions 505 and 506. All three real-model requests completed, and
the process shut down normally. The post-run harness failed its artifact check:
the requested state dump was not written, so it recorded no pre/post state
measurements. The supervisor status is `fail` with return code 1 for this
missing requested artifact, not for a model-service failure.

The verifier route capture places positions 505 and 506 in one two-token
window. The existing `STRATA_VERIFY_DUMP_GDN_STATE` hook only copies state when
`T == 1`; therefore it cannot snapshot these rows. No raw GDN state file was
created. The 512→2,048→512 requests returned 16 completion IDs each. The run
took 181.7 seconds, with 14.35 GiB minimum host/admission availability and zero
cgroup low/high/max/OOM/OOM-kill events.

The failed/unsupported cell is retained here with its `run/` output and
supervisor telemetry. Capturing the two-row window requires a hook that records
the GDN intermediates for `T=2`; no per-token state result is inferred from the
missing dump. Phase 5 remains open.

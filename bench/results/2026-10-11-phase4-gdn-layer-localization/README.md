# Initial GDN layer localization screen — Orin — 2026-10-11

This retained attempt uses the earlier `STRATA_STATE_HASH_GDN` format, which
reported only the low 16 bits of each per-layer hash. Two independent worker-8
IQ1_M processes used the same 512-token prompt, eight-token cap, MTP settings
and 6,519-slot cache. Output IDs/text matched across this pair, but the
aggregate committed state differed at L=512. Its truncated per-GDN hashes
suggested the first difference near ordinal 3; this was not strong enough to
establish layer identity and was superseded by the full-width diagnostic in
the sibling `2026-10-11-phase4-gdn-layer-fullhash/` report.

The complete engine logs, request records, configs and supervisor telemetry
are retained for audit. Minimum availability was 8.33 GiB. The later full-width
run uses the same opt-in path with 64-bit hashes and is the authoritative layer
localization evidence.

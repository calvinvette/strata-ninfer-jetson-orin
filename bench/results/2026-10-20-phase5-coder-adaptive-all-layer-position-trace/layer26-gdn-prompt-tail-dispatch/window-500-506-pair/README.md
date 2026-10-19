# Wider prompt-tail request — verifier coverage limited to 505–506 — Orin — 2026-10-20

This randomized delayed-control/adaptive repeat requested dispatch rows at
positions 500 through 506 with the same binary and Coder IQ1_M model. Both
supervised arms passed (185.8 s delayed, 182.8 s adaptive). Minimum host and
admission availability were 14.28 GiB for delayed and 14.38 GiB for adaptive;
cgroup memory event counters were zero.

The runtime emitted rows only at positions 505 and 506: 192 records per arm,
one initial and one recovery record for each position across 48 layers. It
emitted no rows for requested positions 500–504, so those cells are unsupported
by this verifier dispatch capture in this workload. The exact capture hashes
match the prior same-binary two-position pair: delayed
`d14d87d0dd142cfedd2a0efc769a401184fdee91c096c2a3a18f077c479a8868`; adaptive
`f2ed1861fd751751d870e3140c3b81001f87d7e60f22bd594cb45093d9b0b`.

At the observed positions the result reproduces exactly: delayed control has
matching owners, IDs and activation vectors across initial/recovery; adaptive
cap 8 first changes owner placement at layer 1, activation at layer 26 and
expert IDs at layer 27 for position 505 and layer 31 for 506. Since the earlier
positions were not captured, this does not tell whether the adaptive state
divergence begins before the verifier window.

Per-arm analyzer outputs and full supervisor telemetry are retained beneath
this directory. Phase 5 remains open.

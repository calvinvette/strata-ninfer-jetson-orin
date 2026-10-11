# Verifier device-plan owner check — Orin — 2026-10-10

This follow-up forces `STRATA_VERIFY_DEVICE_PLAN=1` on the existing Q2_0 batch
owner smoke. The serial control and two-slot candidate each handled one-token
requests for inputs 32 and 33. The candidate admitted both slots. Outputs were
220 and 248046, matching the default-route batch control, and all nine
persistent-state hashes matched by prompt identity. The comparison is captured
in `cross-mode-comparison.json`; this is functional evidence, not a performance
claim.

The traced verifier allocated and freed 64 bytes for the device-plan skip
scratch and 40,000 bytes for the 5,000-entry device slot-offset copy. The
profile buffer (12,704 bytes) and batch verifier arena (37,120 bytes) also
balanced. Owner accounting counted 283 allocations and 280 frees; the only
live device payload at log end was the primary and two batch service-lifetime
session backings (705,102,336 requested bytes total), as in the default batch
run. Minimum physical `MemAvailable` was 16,428,920,832 bytes (15.30 GiB), well
above the six-GiB floor. The owner ledger remains partial and excludes graph
executable/driver memory.

The native CUDA binary is the same build recorded in the [batch-session owner
report](../2026-10-10-phase3-batch-session-owners/README.md); no source changed
for this environment-only check. Raw supervisor telemetry, engine logs and
owner accounting are under `orin-supervisor/` and `engine-runs/`. The Q2_0
artifacts remain under `~/models/strata-orin-validation/`.

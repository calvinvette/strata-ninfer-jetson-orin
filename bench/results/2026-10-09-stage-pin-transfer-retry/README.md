# Page-cache-only transfer retry — no stage coverage

This supervised run fixed state hashing and used the same exact 4,096-token
prompt, but `STRATA_IO_PREFETCH=1` left `STRATA_IO_PF_STAGE` unset. Strata filled
the OS page cache without allocating stage buffers; neither arm emitted an
`expert-stage-*` owner. Generated token IDs matched, while six persistent state
fields differed between the spec4 processes. Minimum available memory was
7,835,275,264 bytes (7.30 GiB), above the six-GiB floor.

The instrumentation correctly rejected the run for missing stage ownership and
state parity. It is retained as an unsupported/no-coverage attempt and is not
included in the fixed-cache transfer summary. See the
[completed staged screen](../2026-10-09-stage-pin-transfer-fixed/README.md).

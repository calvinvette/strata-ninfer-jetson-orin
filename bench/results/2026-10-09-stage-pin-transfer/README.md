# Exploratory stage-pin attempt — incomplete

This initial supervised run used the 4,096-token prompt and 64-token output,
but the helper forced `--prompt-cache 0` while state fingerprints require a
positive prompt-cache setting. It generated the pageable arm and maintained the
six-GiB floor (minimum available 8,119,345,152 bytes), then failed because no
state fingerprint was present. It did not run a valid pinned/pageable pair and
emitted no expert-stage events. Preserve as a harness failure; the corrected
fixed-cache experiment is in
[the completed transfer screen](../2026-10-09-stage-pin-transfer-fixed/README.md).

The run used `STRATA_IO_PREFETCH=1` without the staging selector, so it also
did not exercise the expert-stage pool. No performance result is claimed.

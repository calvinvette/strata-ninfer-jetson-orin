# Cgroup pressure probe with scope accounting — Orin — 2026-10-11

A 4 GiB anonymous allocation was held for 15 seconds inside a transient
systemd user scope capped at 6 GiB. The first sampler version recorded both
the transient scope and its uncapped session ancestor, so its printed peak was
not scope-specific; those raw samples are retained at the directory root and
are excluded from the result below.

The fixed sampler reads the launched `systemd-run` process's cgroup membership
on every sample and records only the actual `run-*.scope` leaf. It captured 63
scope samples out of 64 host samples. The leaf reported `memory.max` as 6 GiB
and peaked at 4,306,341,888 bytes (4.01 GiB). The child exited successfully
and reported the full 4,294,967,296-byte allocation. Minimum host
`MemAvailable` was 22,960,836,608 bytes (21.39 GiB), well above the ordinary
six-GiB floor.

This closes the sampler's scope-attribution gap for this bounded host-memory
probe. It does not test Strata inside the capped scope, GPU backing attribution,
or service recovery under active pressure. The corrected script, raw JSON and
outputs are in `fixed/`; the first attempt remains available for audit in the
parent directory.

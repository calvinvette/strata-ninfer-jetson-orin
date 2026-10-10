# Mapped versus pread energy diagnostic — Orin — 2026-10-10

This diagnostic added opt-in `tegrastats` rail and clock sampling to the file-tier
transfer harness. Its initial runs used `--expert-cache auto`, so residency
changed between processes. The first used `spec2` without MTP and mismatched
state in all three pairs; its supervisor minimum physical availability was
7,801,102,336 bytes (7.27 GiB). The corrected 8K `spec4`/MTP repeat also used
automatic sizing and selected between 7,035 and 7,108 expert slots across its
six arms.

All tokens matched in the `spec4` repeat, but only pair 0 matched persistent
state; pairs 1 and 2 differed in GDN, PLE, tail, pooled, pooled-full and KV.
Same-mode automatic-cache repeats likewise chose different cache capacities.
This invalidated timing and energy interpretation because cache residency can
change whether a routed expert is computed on the GPU or CPU.

For diagnosis, the old auto-cache `VIN_SYS_5V0` system-input rail estimates were
179.6–190.8 J per request. The sampler recorded CPU frequencies, but this
tegrastats output did not expose GPU or EMC frequencies. These values include
unrelated system activity and are not process-attributed. The follow-up
[fixed-cache screen](../2026-10-10-phase3-transfer-energy-fixed-cache/README.md)
matched tokens and persistent state in all three pairs and retains its own
screening-only timing and rail telemetry.

Preserve these mismatched-residency attempts as failed cells, and use an explicit
cache target in future transfer comparisons. Both raw runs are retained. No
model or build artifacts are included.
The corrected run's complete raw records are in
[`2026-10-10-phase3-transfer-energy-spec4`](../2026-10-10-phase3-transfer-energy-spec4/).
The [same-mode controls](../2026-10-10-phase3-transfer-state-repeat/README.md)
record why the original auto-cache parity failures first appeared.

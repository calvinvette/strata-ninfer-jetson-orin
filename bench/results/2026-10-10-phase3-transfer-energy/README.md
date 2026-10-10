# Mapped versus pread energy diagnostic — Orin — 2026-10-10

This diagnostic added opt-in `tegrastats` rail and clock sampling to the file-tier
transfer harness. It is not a qualified transfer result: the first run used the
minimal `spec2` configuration without MTP and failed the persistent-state check
in all three pairs even though token IDs matched. Its raw samples and logs are
retained in `experiment/`; supervisor minimum physical availability was
7,801,102,336 bytes (7.27 GiB).

The corrected three-pair rerun used the existing 8K `spec4`/MTP configuration,
the same exact formatted 512-token prompt and 64 generated tokens, and randomized
mapped/pread order. All pairs emitted the same token IDs, but only pair 0 matched
the recorded persistent-state fingerprints. Pairs 1 and 2 differed in GDN, PLE,
tail, pooled, pooled-full and KV state. The process therefore exited failed, and
the energy and timing observations must not be used to rank the paths. Minimum
physical availability was 7,766,663,168 bytes (7.23 GiB), above the six-GiB
supervisor floor.

For diagnosis, the reported `VIN_SYS_5V0` whole-board rail energy estimates were
179.6–190.8 J per request. The sampler also recorded CPU frequencies, but this
tegrastats output did not expose GPU or EMC clock rates. Rail energy includes
unrelated board activity and is not attributed to the process. With persistent
state parity unstable, these are telemetry checks only, not energy-per-request
comparisons. The original `spec2` attempt is retained separately at
`../2026-10-10-phase3-transfer-energy/` (this directory is its parent).

The discrepancy requires a dedicated determinism diagnosis before further
transfer tradeoff runs. Preserve the passing earlier screen as inherited
evidence, but do not treat it as confirmation of this failed repeat. Both runs,
including failures, are retained. No model or build artifacts are included.
The corrected run's complete raw records are in
[`2026-10-10-phase3-transfer-energy-spec4`](../2026-10-10-phase3-transfer-energy-spec4/).

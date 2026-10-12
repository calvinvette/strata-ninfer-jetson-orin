# Eager MTP2 cancellation and recovery — 2026-10-12

This run applies the accepted-prefix cancellation harness to the eager routed
expert path (`--no-capture`) with MTP window 2. It uses the same Q2_0
integer-list prompt and fixed 3,000-slot cache as the existing captured-path
[cancellation result](../2026-10-13-phase5-q2-mtp-cancel-recovery/README.md).
Three fresh exact-length references check the canceled request's committed
state, and the canceled service handles a recovery request before teardown.

The eager stream was closed after one visible delta. The engine had committed
three tokens over two accepted-prefix transactions (`L=48` and `L=50`), with
one accepted draft. Cancellation was reported by the engine; the same service
then returned exactly `Hello Orin!`. All three fresh references matched the
canceled token sequence and all eleven state fields at each accepted prefix,
and matched each other. Direct comparison with the captured-path result found
the same token IDs and identical state at both prefixes.

The run passed under a 28-GiB cgroup ceiling, retaining the six-GiB floor. The
minimum host availability was 17.09 GiB and minimum effective admission
headroom was 12.73 GiB. Clock sampling was read-only and dynamic; EMC access was
denied. Energy was not measured. This adds one cancellation/recovery point for
the eager route; it does not cover cancellation during long prefill, broader
pressure, or task quality.

`run/result.json`, per-process engine logs, memory/tegrastats records and
`supervisor/result.json` preserve raw evidence. `captured-eager-parity.json`
records the direct comparison and current binary SHA256.

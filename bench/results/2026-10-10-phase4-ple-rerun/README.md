# Artifact-aware Q2_0 PLE test rerun — Orin — 2026-10-10

The requested PLE test was rerun after the worker screen using the existing
Q2_0 shard and generated pack in `~/models/strata-orin-validation/`. The
artifact-aware `ple_parity --selftest` command passed under the six-GiB
supervisor (exit 0; minimum sampled availability 24.53 GiB). Its detailed
seven-stage numerical result remains in the earlier
[artifact-aware oracle report](../2026-10-10-phase3-q2-ple-artifact-aware/README.md).

An attempted CTest invocation from `build/integration/control` could not run
because that stale build directory had no `ple_parity` executable. The direct
candidate binary run above is the valid rerun; the missing stale executable is
recorded here so it is not mistaken for a numerical test failure.

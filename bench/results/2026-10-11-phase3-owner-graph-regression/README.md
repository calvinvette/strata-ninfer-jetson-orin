# Failed regression launcher invocation — Orin — 2026-10-11

This supervisor record is retained for audit. The test command mistakenly used
`python3 -m ctest`; Python has no `ctest` module, so it exited immediately with
status 1 before starting any tests. Minimum host `MemAvailable` remained 24.63
GiB. No CTest result is claimed from this directory.

The same selection was rerun successfully using the `ctest` executable. See
[the successful regression](../2026-10-11-phase3-owner-graph-regression-retry/README.md).

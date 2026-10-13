# Q2_0 PLE and Phase 3 regression refresh — Orin AGX — 2026-10-13

A fresh run on the current checkout repeated the artifact-aware Q2_0 PLE oracle,
the selected Phase 3 CTests, and integration Python discovery. The Q2_0 model
and PLE artifacts were already present under `~/models/strata-orin-validation/`;
nothing was downloaded or copied into Git.

| Check | Result | Duration | Minimum host/effective availability |
| --- | --- | ---: | ---: |
| Artifact-aware `ple_parity --selftest` | Pass; 7 numerical stages, 3 tokens; worst relative L1 `1.148e-7` | 2.22 s | 24.284 GiB |
| Selected Phase 3 CTests | 15/15 passed, serial | 19.86 s | 24.407 GiB |
| Integration Python discovery | 130/130 passed | 6.36 s | 24.377 GiB |

Each command ran in a separate `systemd-run --user --scope` with
`MemoryMax=28G`, a six-GiB host/effective availability floor, and read-only
clock sampling. No cgroup `high`, `max`, `oom`, or `oom_kill` events were
recorded. EMC frequency sampling was denied by the system; energy was not
process-attributed. No clock or service controls were changed. Raw command,
stdout/stderr, memory samples and tegrastats are retained in the three run
folders.

The checked `ple_parity` executable SHA256 is
`021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30`; the
serving executable is
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.
These are the same binaries recorded in the post-soak refresh. This rerun
reconfirms the already-closed Phase 3 scope; it does not price private CUDA
Graph backing, establish a general capacity boundary, or qualify another
model/backend.

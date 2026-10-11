# Q2_0 decode cancellation and recovery under cgroup pressure — Orin — 2026-10-11

This run checks whether a streamed Q2_0 decode can be disconnected and followed
by a short request in the same service process under a 22 GiB `MemoryMax`
cgroup, while the standard supervisor preserves six GiB of effective physical
availability. The stream produced visible text, was closed by the client during
decode, and the next request returned exactly `Hello Orin!`; the server stayed
alive. The engine marked the request cancelled after three tokens had been
committed. This adds a decode-cancellation point to the earlier pressure test
that cancelled during prefill.

The 22 GiB scope passed. Minimum physical `MemAvailable` was
22,960,861,184 bytes (21.38 GiB); minimum effective cgroup availability was
10.26 GiB. The instrumented owner trace balanced 302 allocations and frees:
session 1, expert cache 1, pageable expert staging 256, prefill 27, mapped
verifier host staging 16, and verifier 1. These events do not account for all
driver or graph-pool memory. No performance or quality claim is made.

The test used the Q2_0 model and pack under `~/models/strata-orin-validation/`
with the current candidate binary (SHA256
`aaa426d3e73a9b4d12a5751069a21331619001aedcbdbc15be8b6c6ac8d46856`). The
server configuration and small standard-library service harness are retained
in `rerun3/`; the supervisor retained cgroup/physical memory samples and
tegrastats output. The command was:

```sh
systemd-run --user --scope -p MemoryMax=22G \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-11-phase3-q2-decode-cancel-22G/rerun3/supervisor \
  --interval 0.5 --timeout 900 -- \
  python3 bench/results/2026-10-11-phase3-q2-decode-cancel-22G/rerun3/run_service.py
```

Two earlier harness starts in this directory are retained but excluded: one
stopped before requests because `requests` was unavailable in the host Python;
the next exposed a harness import-path mistake. Neither is an engine failure.
Phase 3 remains open for broader admission and graph-memory attribution beyond
these exercised model/configuration points.

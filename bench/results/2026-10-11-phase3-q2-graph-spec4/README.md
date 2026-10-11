# Q2_0 native verifier spec4 graph and NVMap probe — Orin — 2026-10-11

This diagnostic widens the Q2_0 native verifier from `--spec 2` to `--spec 4`
at the same 4K configured context and 256-slot expert cache, then samples the
process-owned Tegra NVMap IOVMM bytes around the first request. The request
completed with 24 output tokens. The engine captured a six-token verifier
window and a one-token window. The CUDA Driver interposer observed three
successful graph instantiations, and the integration owner trace attributed
two to `verifier` and one to `verifier-commit-graph`.

For the engine PID, twenty NVMap samples before the first graph call were
stable at 5,249,032,192 bytes. Twenty samples after the last successful call
were stable at 5,297,741,824 bytes: a net increase of 48,709,632 bytes
(46.45 MiB) over the capture/instantiate interval. The earlier spec2 Q2_0
run measured 72,425,472 bytes over four graph calls. These are separate
startup intervals with different observed calls; neither isolates graph
executable size, and the difference is not a per-graph cost or evidence that
spec4 uses less memory in general.

The six-GiB availability supervisor passed. Minimum host `MemAvailable` was
23,012,356,096 bytes (21.43 GiB). The 302 instrumented owner allocations
balanced 302 frees: session 1, expert cache 1, pageable expert staging 256,
prefill 27, mapped verifier host staging 16, and verifier 1. The public
Driver interposer observed no allocation calls inside graph instantiation;
NVMap is the independent device-owner counter used for the interval.

The Q2_0 artifacts remain under `~/models/strata-orin-validation/`. Candidate
binary SHA256: `aaa426d3e73a9b4d12a5751069a21331619001aedcbdbc15be8b6c6ac8d46856`.
The exact server configuration, one-request harness, raw NVMap samples,
engine/driver traces and supervisor telemetry are retained in this directory.
This expands coverage to one wider native verifier shape; legacy session-token
graphs, other graph pools and non-NVMap allocations remain unpriced.

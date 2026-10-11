# Batch-session and verifier batch-owner smoke — Orin — 2026-10-10

The integration owner trace now records `session-stage` and `session-batch`
backing separately from the primary `session` arena. The arrays carved inside
a session are not counted again. The trace intentionally keeps the stage and
batch session owners live at process teardown because those buffers are held for
the service lifetime; a live row is not classified as a leak. Explicit session
release remains a separate cleanup gate.

A supervised Q2_0 run started a serial control service, then a service with
`--batch 2`, using the existing native Q2_0 shards, pack and expert profile in
`~/models/strata-orin-validation/`. Two concurrent deterministic one-token
requests used input IDs 32 and 33. The engine admitted both slots. Outputs were
220 and 248046 in both arms, and all nine persistent-state hashes matched by prompt identity (`ple_prev`) for
each completed request in two independent runs. Both runs enabled verifier profiling and state hashing;
this is functional and allocation evidence, not timing evidence. No model was
downloaded and no clocks or service outside these test processes changed.

The two `session-batch` allocations each requested 235,034,112 bytes (0.22
GiB); with the 235,034,112-byte primary session, the observed session backing
remaining live at log end totals 705,102,336 requested bytes on CUDA device 0.
The verifier batch arena requested 37,120 bytes and had a matching free. Its
12,704-byte profile buffer also balanced. Across the instrumented log, 281
allocation events and 278 frees leave only the three service-lifetime session
backings live. Maximum host `MemAvailable` was not the issue; minimum observed
`MemAvailable` was 16,427,282,432 bytes (15.30 GiB), safely above the preserved
six-GiB floor. The owner ledger reports a 7,662,876,576-byte concurrent
requested-device peak for its instrumented allocations; this is a partial
attribution ledger, not total physical memory. Graph executable/driver bytes
remain unpriced.

The native CUDA `strata` build passed on Orin. maestro1 rebuilt the same changed
generator source for HIP with one job, and its CLI help exited 0; this is
compile/help evidence only and does not claim a HIP runtime result. The SYCL project uses a separate
generator source. The owner parser and run-control Python suites passed 29
tests, and the batch smoke harness passed Python compilation.

`orin-supervisor/` and `engine-runs/` preserve the second run telemetry, both
engine logs, results, and parsed owner accounting. `repeat-1/` preserves the
first independent run. `initial-harness-attempt/` records the
first wrapper launch failing before engine startup because the default Python
lacked `jinja2`; the retry used the existing model-validation virtualenv and
passed without installing packages. The exact reproduction harness is
`run-batch-owner-smoke.py`.

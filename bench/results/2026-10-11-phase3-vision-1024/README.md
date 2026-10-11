# 1,024-token vision admission smoke — Orin — 2026-10-11

The vision smoke harness now accepts explicit minimum/maximum image-token
limits. This run used both limits at 1,024 and a generated 2,048×2,048 PNG
with a two-color field, repeated horizontal lines and a circular outline. The
fixture SHA-256 is
`c594b1e0f86f7f0b4a653e291e85ff37b3b894b2f517d7a4129d83f9eab65b8d`.

The optional CUDA `strata-vision` build (SHA-256
`69d6a171c0ff29504a5971116f7a9299dc7abf0ae1f6caa1563f009684e96825`)
served the image through the candidate IQ1_M service (SHA-256
`5de05658f9b91f1b5a416b49285bc21fbc441f0fb0747b45d9f2f840fbbccb47`).
The API returned HTTP 200 with 1,049 prompt tokens, 48 output tokens and a
non-empty description. The request took 57.90 seconds. The engine log records
all 1,049 prompt tokens consumed; the image cap was configured to 1,024.

The six-GiB physical-memory supervisor observed a minimum host `MemAvailable`
of 7,521,767,424 bytes (7.005 GiB), leaving about 1.005 GiB above the floor.
The run passed without supervisor interruption; cgroup low/high/max/OOM/OOM-kill
counters were zero. The model resolved a 5,000-slot requested expert cache to
6,325 actual slots (12.03 GiB shared RAM). Preserve the supervisor's memory
samples, tegrastats, service config, API result and engine log here.

This is a single admission/functional point for one large synthetic image and
the existing IQ1_M MTP configuration. It does not measure vision accuracy,
image complexity variation, the whole 1,024-token operating envelope, energy,
or a paired baseline. The encoder's CUDA allocations were not separately
interposed in this run. The earlier PID-tagged CUDA allocation probe remains a
lower-bound observation for its 16-token setup. This result does not close
Phase 3's broader admission or unique-backing accounting gates.

Reproduce from the repository root with the exact command stored in
`supervisor/result.json`; the run used `tools/integration/run_control.py` with
its default six-GiB floor. No model artifacts or build products are stored in
Git.

## PID-tagged CUDA runtime allocation repeat

A second identical 1,024-cap run used the existing test-only CUDA runtime
interposer, inherited by both `strata-vision` and the main engine. It again
returned HTTP 200 with 1,049 prompt tokens. The supervisor passed with minimum
host availability of 9,241,104,384 bytes (8.606 GiB); this is a separate run
with different cache state, not a paired memory comparison.

The encoder process made six observed `cudaMalloc`/`cudaFree` events, peaked at
1,037,613,696 bytes (989.5 MiB), and returned its tracked current bytes to
zero at exit. The engine process peaked at 17,371,062,992 bytes (16.18 GiB) in
tracked CUDA runtime requests and had 1,476,945,656 bytes (1.375 GiB) still
tracked at shutdown. The engine's peak includes model/service allocations and
the image request; it is not an isolated vision increment. These ledgers are
per-process request totals and must not be added to each other or treated as
physical backing. They omit CUDA driver/internal, graph-executable, pool and
vendor-library allocations. PID/event counts and byte values are in
`alloc-experiment/allocation-summary.json`; raw logs and the supervised
telemetry are retained alongside it.

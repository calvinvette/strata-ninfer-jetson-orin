# Vision-enabled candidate memory observation — Orin — 2026-10-10

The optional CUDA image encoder was built in the ignored
`build/integration/vision-cuda/` directory for ARM64/SM87 with CUDA 12.6.68,
using one compile job and the llama.cpp dependency tree already used by the
candidate build. No tracked Strata source or default path changed. The encoder
SHA-256 is `69d6a171c0ff29504a5971116f7a9299dc7abf0ae1f6caa1563f009684e96825`;
the candidate engine SHA-256 is `8da2ee4299832c1715b07c9dfa2287453c492b48e4e4d96929ff54c1438636df`.
The projector and test image SHA-256 values are retained in the experiment
configuration/result and match the local `~/models` projector and checked-in
56×56 fixture.

A loopback API server loaded the same IQ1_M model, MTP and cache/context setup
as the other Phase 3 controls, with images enabled and the 16-token encoder cap.
The real image request returned HTTP 200, used 41 prompt tokens, emitted 48
tokens, and described the checkerboard/gradient fixture. The encoder loaded in
1.8 seconds and warmed up in 0.5 seconds. This is a small-image description
smoke test; it does not qualify high-resolution images, grounding accuracy or
the recommended 1,024-token grounding path.

The supervised run passed with minimum host `MemAvailable` of 7,751,241,728
bytes (7.22 GiB), above the ordinary 6-GiB floor. Strata reported 7,427 MiB
CUDA free after the verifier/drafter bind and 7,431 MiB shared RAM available
with everything loaded, including its 6-GiB headroom policy. The configured
5,000-slot cache resolved to 6,446 actual slots (12.26 GiB); this is a device
sizing lower-bound behavior, not a measured capacity improvement. The main
engine's observed allocation-request peak was 13,836,395,984 bytes. The report
excludes the separate `strata-vision` process's allocations and CUDA graph-pool
bytes; the two verifier graph instantiations were counted but not priced.
System-wide memory telemetry includes both processes and the image request,
but energy and GPU/EMC clock rates were not measured.

`supervisor/` preserves the image response, engine/server logs, memory samples,
tegrastats and owner-accounting summary. `run_vision_smoke.py` reproduces the
bounded API request; it uses the paths passed on the command line and writes
all runtime artifacts beneath its output directory. Model artifacts and the
CUDA encoder build remain outside Git.

## Separate-process CUDA allocation probe

A test-only `LD_PRELOAD` probe wrapped successful CUDA runtime `cudaMalloc`,
`cudaMallocManaged` and `cudaFree` calls and tagged each record with PID. The
corrected supervised image request passed HTTP 200, returned 41 prompt tokens
and 48 output tokens, and completed in 10.34 seconds. Minimum host
`MemAvailable` was 7,740,080,128 bytes (7.21 GiB).

The `strata-vision` PID peaked at 913,686,144 bytes (871.4 MiB) in tracked
runtime allocations during model load/warmup; its tracked current bytes returned
to zero on process exit. The separate main-engine PID reached a tracked
19,027,389,968-byte (17.72 GiB) high-water mark. Do not add these numbers to
each other or to host RAM: they are concurrent API allocation ledgers on one
unified-memory device, while the supervisor's host availability is the physical
memory authority. The passing supervised run is the admission evidence.

This probe is a lower bound: it does not interpose CUDA driver allocation APIs,
stream-ordered pools, graph executable resources or all vendor-library internal
allocations, and it does not identify which process caused the full system
physical-memory peak. The original vision smoke report's owner trace also omits
those scopes. Treat these PID-tagged CUDA calls as attribution evidence, not a
complete memory total. Source, build command/hash, probe output, and the
supervisor's full telemetry are retained under `alloc-probe/`. Its first
invocation failed before making an image request because it named a fixture
path that does not exist in this checkout; that failed run is retained in
`alloc-probe/supervisor/` and the corrected run is in `alloc-probe/supervisor2/`.

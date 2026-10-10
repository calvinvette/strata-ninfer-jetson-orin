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

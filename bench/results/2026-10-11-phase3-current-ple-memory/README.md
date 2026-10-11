# Current-binary Q2_0 PLE and Phase 3 regression rerun — Orin — 2026-10-11

The Q2_0 artifact-aware PLE oracle passed against the current candidate binary
under the six-GiB physical availability supervisor. It checked three tokens
through all seven stages, with worst relative L1 error `1.148e-7`. The test
reassembled the native type-42 Q2_0 key byte-for-byte and matched the native
projection against the independently decoded path. PLE table rows and layer-1
weights are real; hidden state and convolution history are synthetic. This is
block-level numerical evidence, not whole-model quality or performance evidence.

The focused ten-test Phase 3 CTest set also passed under the same supervisor:
VMM, dense PLE keys, segmented and memory-limited expert cache, allocation
refusal, platform memory admission, pinned fallback/shared behavior, and PLE
oracle/reader. Minimum sampled `MemAvailable` was 24.54 GiB for the suite and
24.64 GiB for the direct PLE test. The owner-observation summarizer's 20 unit
tests passed as well.

The PLE executable SHA256 is
`021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30`;
`strata` SHA256 is
`3fc0f58108c14e5e33bcfbf1092f1b377b132451ae77305878ca406f70d397f1`.
The model shard and generated pack remain under `~/models/strata-orin-validation/`.
Raw output and physical-memory telemetry are retained in
`../2026-10-11-phase3-q2-ple-current/supervisor/` and
`../2026-10-11-phase3-memory-ctest-current/`.

These reruns confirm selected numerical and ownership contracts. They do not
close graph executable/driver memory attribution, broad cgroup-pressure
behavior, or remaining transfer/admission gates; no default changed.

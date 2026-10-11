# Current-checkout Q2_0 PLE oracle rerun — Orin — 2026-10-11

The current candidate's artifact-aware `ple_parity --selftest` passed under
the ordinary six-GiB physical-availability supervisor. It checked all seven
PLE stages for three tokens, reconstructed the native Q2_0 key bytes exactly,
and matched the native projection against the independently decoded path.
Worst relative L1 error was `1.148e-7`; no non-finite values were reported.
The Q2_0 table and layer-1 weights are real; hidden state and convolution
history are synthetic. This is operator-contract evidence, not whole-model
quality or serving-performance evidence.

The PLE executable SHA256 was
`021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30`.
The model shard and pack remain under `~/models/strata-orin-validation/`.
The supervisor sampled minimum host `MemAvailable` of 26,459,758,592 bytes
(24.64 GiB). Raw output and telemetry are retained in `supervisor/`.

The same current candidate passed the selected 15-test Phase 3 accounting and
owner CTest set sequentially under the six-GiB supervisor: shared-memory
budget, conversation memory/cache, VMM, native PLE key, per-layer and
segmented cache, cache allocation/refusal, platform admission, pinned fallback
and shared registration, PLE oracle/reader, and convolution cache. Minimum
host availability was 26,422,337,536 bytes (24.60 GiB). Raw CTest output and
telemetry are retained in `../2026-10-11-phase3-accounting-rerun/supervisor/`.

These reruns reconfirm selected numerical and ownership contracts. They do not
price other model graph paths, establish broad cgroup-pressure behavior, or
close remaining transfer/admission gates. No runtime default changed.

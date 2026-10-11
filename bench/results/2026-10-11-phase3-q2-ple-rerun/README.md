# Q2_0 PLE oracle rerun — Orin — 2026-10-11

The artifact-aware PLE oracle was rerun against the current candidate binary
under `tools/integration/run_control.py` with the ordinary six-GiB physical
availability floor. It passed all seven stages for three tokens; worst stage
relative L1 error was `1.148e-7`. The check reassembled the native type-42 Q2_0
key blocks byte-for-byte and matched the native projection against the
independent decoded path. The PLE table rows and layer-1 weights are real;
hidden state and convolution history are synthetic. This is block-level
numerical evidence, not whole-model quality or performance evidence.

The minimum sampled `MemAvailable` was 26,469,761,024 bytes (24.66 GiB), above
the six-GiB floor. The model shards and generated pack remain in
`~/models/strata-orin-validation/`; nothing was copied into the repository.
Raw command, stdout/stderr and telemetry are in `supervisor/`.

Candidate `ple_parity` SHA256:
`021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30`.

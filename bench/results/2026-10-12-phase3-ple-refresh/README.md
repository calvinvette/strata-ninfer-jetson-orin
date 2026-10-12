# Q2_0 PLE and Phase 3 regression refresh — Orin — 2026-10-12

The current `ple_parity` executable (`SHA-256 021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30`) passed its artifact-aware self-test using the Q2_0 dense pack and GGUF table shard 2 under the six-GiB memory supervisor. All seven PLE stages passed for three tokens; worst relative L1 error was `1.148e-7`, with no non-finite values. Minimum host `MemAvailable` was 24.58 GiB.

The same-day selected ownership/graph CTest set passed 19/19 serially, with 24.48 GiB minimum host availability. Integration Python discovery passed 113/113, with 24.54 GiB minimum. These checks cover selected allocation, transfer, cache, VMM, PLE and captured-graph contracts; they do not qualify full model quality, complete physical backing, broad pressure recovery or transfer performance.

Commands, stdout/stderr, supervisor samples, cgroup observations, clock samples and tegrastats are retained in `ple/`, `ctest/` and `python/`. Models remain under `~/models`; the model paths and identities are in each result/config record. No model or build products are tracked. Clocks were observed without control; energy was not measured.

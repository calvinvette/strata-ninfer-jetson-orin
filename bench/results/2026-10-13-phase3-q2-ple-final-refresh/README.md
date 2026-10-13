# Q2_0 PLE and Phase 3 regression refresh — Orin — 2026-10-13

The current candidate build passed a fresh supervised, artifact-aware PLE check
against the Q2_0 PLE pack and GGUF under `/home/calvin/models/strata-orin-validation/`.
All seven numerical stages passed for three tokens; worst relative L1 error was
`1.148e-7`. The selected memory/owner/PLE CTest set passed 15/15, and integration
Python discovery passed 124/124.

Each command ran in its own `systemd-run --user --scope` with a 28-GiB cgroup
limit and the runner's 6-GiB host/effective availability floor. Minimum host
availability was 24.40 GiB for PLE, 24.55 GiB for CTest, and 24.53 GiB for
Python tests. Clock sampling was read-only; EMC frequency access was denied,
energy was not measured, and no clocks or services were changed. Raw runner
telemetry and command output are retained in this directory. Binary SHA256
identities are in `SHA256SUMS.txt`.

This refresh confirms selected Phase 3 contracts on this build. It does not
price private CUDA Graph backing, establish a general capacity threshold, or
extend model-quality evidence. Model and pack files remain outside Git under
`/home/calvin/models/`.

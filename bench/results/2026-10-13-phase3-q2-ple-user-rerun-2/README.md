# Q2_0 PLE and Phase 3 regression refresh — Orin — 2026-10-13

The current candidate binary (`1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`) passed a fresh supervised, artifact-aware PLE parity self-test against the Q2_0 PLE pack and GGUF under `/home/calvin/models/strata-orin-validation/`. All seven numerical stages passed for three tokens; worst relative L1 error was `1.148e-7`.

The serial memory/owner/PLE CTest selection passed 15/15 in 16.62 seconds. Integration Python discovery passed 124/124 in 6.40 seconds. All three commands ran with the six-GiB availability floor; minimum host and effective availability were 24.58 GiB for PLE, 24.39 GiB for CTest, and 24.56 GiB for Python tests. Clock sampling was read-only; EMC rate access was denied, energy was not measured, and no clocks or service settings were changed.

Raw supervisor telemetry, command output and results are retained beside this report. The tests refresh selected Phase 3 contracts only. They do not price private CUDA Graph backing, establish general capacity, or extend model-quality evidence. Models and packs remain outside Git under `/home/calvin/models/`.

# maestro1 HIP/SYCL build check

Current source commit `0ddbf031` plus the overlay in
`../source-overlay.diff` was built from a tracked-source snapshot on maestro1.
The snapshot omitted benchmark records, documentation, web assets and the
immutable `reference/ninfer/` tree. HIP used ROCm 7.10.0a20251120 and gfx1100;
SYCL used oneAPI DPC++ 2026.1.1. Both builds used one job and completed
compile/link successfully. The HIP tree was incrementally reconfigured and
rebuilt after syncing the final CMake test-registration change. Both binaries'
`--help` checks passed with their respective runtime library environments.

| Build | Result | Binary SHA256 |
| --- | --- | --- |
| HIP, gfx1100 | Pass | `b74d0e7109b3fc3aee34f7165fd436cf3fab539783b381c54b3ed682c56937e2` |
| SYCL, oneAPI 2026.1 | Pass | `9aab758eeeb9fe561f205959398746747de7a19e75d5fca15e6a34c611f7d1d1` |
| HIP `native_expert_parity` | Pass, linked | `e50b908e16c7d02620ef586c8d29fcfc372e12bd5b786636fbca77239c2ff13d` |

The shared CPU expert source compiled under both backend configurations. HIP
also compiled and linked the updated `native_expert_parity` target. The initial
HIP log shows 314 numbered Ninja steps with a 315-step total; the build command
returned success, generated its binary hash, and the subsequent incremental
reconfigure completed successfully. This is x86_64 compile/link and CLI-help
evidence only. maestro1 has no AMD/SYCL GPU qualification here; no model,
accelerator runtime or performance result is claimed. Logs and toolchain output
are retained alongside this note.

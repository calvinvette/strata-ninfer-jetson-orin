# Current-source MTP reset backend builds — maestro1 — 2026-10-14

This report checks that the shared MTP request-boundary fix from commit
`2b6dc076` compiles and links in the HIP and SYCL service executables. It is
x86_64 compile and CLI-load evidence from maestro1, not GPU runtime or Orin
performance evidence.

The isolated source snapshot was based on `eee15abe` and contained 2,057 files;
the only three changes over that base were:

| File | SHA256 |
| --- | --- |
| `include/strata/core/mtp.hpp` | `14ad22b78a88070ba09c1121a7e330b174752795eba4f9df5b87da09535f7c4d` |
| `src/core/mtp.cpp` | `d38161933adbe44fa6b05c014506c089258b7da94c914f156012ca6eb6723fb4` |
| `src/program/generate.cpp` | `5d5246a8459eb347d0943cf32e2b41479b21b898542b5201624086855c7600cf` |

The verified source files match those hashes. The complete snapshot hash
manifest was checked on maestro1 before building. Build commands used one job
to fit the host's 3.7-GiB RAM and 4-GiB swap:

- HIP: configure with the pinned ROCm SDK for `gfx1100`, then
  `cmake --build build-hip --target strata native_expert_parity --parallel 1`.
  Both targets linked. `build-hip/strata --help` loaded successfully. Binary
SHA256: `a09109d4029f74f72aa9c8d35c5a47f2132aa4a8308a438623815d854027c4fb`.
- SYCL: configure with Intel oneAPI DPC++ 2026.1.1 and the pinned CMake 3.31.10,
  then `cmake --build build-sycl --target strata --parallel 1`. The service
  linked at 123/123 steps. `build-sycl/strata --help` loaded successfully.
  Binary SHA256: `8cd45c884e2da83460a8766eec53c0d81f0d09c5520a379588df1cfb3c30509a`.

The HIP build log contains compiler warnings but no errors. The SYCL build also
completed with oneAPI warnings, including a GCC installation preference notice;
there were no compile or link errors. Full logs, configure records, help output,
binary hashes, compiler version and host identity are retained in `logs/`.
The initial broader all-target HIP build was intentionally stopped at 91/315
after confirming it included many unrelated test and utility targets; its
partial log is kept separately as `logs/hip-build.txt`. The targeted service
and parity build above completed successfully.

These results qualify only compilation, linking and command-line startup on
maestro1. They do not qualify HIP/SYCL device execution, model behavior,
latency, or any Orin configuration. Orin CUDA build and runtime checks are
recorded in the Phase 5 cancellation/state report. No build products or model
artifacts were added to Git.

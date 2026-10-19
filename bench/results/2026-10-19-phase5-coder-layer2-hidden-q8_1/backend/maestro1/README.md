# maestro1 HIP and SYCL build evidence

The updated shared CPU source and parity diagnostic were copied into the
existing isolated maestro1 source snapshot and both backend builds completed.
HIP used ROCm 7.10.0a20251120 for gfx1100; SYCL used oneAPI DPC++ 2026.1.1.
The build script used two parallel jobs and compiler temporary files under
`/dev/shm/phase5-q8-selector-maestro1/tmp`. All recorded cgroup memory event
counters were zero. Both `strata --help` checks exited 0.

| Build | Result | Binary SHA256 |
| --- | --- | --- |
| HIP `strata` | Pass | `521b28649aae4cb09e8f4848be78a760f954a452ecfa9681e36afeb5ff981664` |
| HIP `native_expert_parity` | Pass | `63a5fdfd3d8235bf79060a6f444ab5b817a42c51eac2d9be984837fa58d2f334` |
| SYCL `strata` | Pass | `d624dce6c9094bacec584c1e6c0d2546973a3d436803ad00e267df69f5bc870c` |

The exact transferred source hashes are in `source-sha256.txt`; command output,
compiler warnings, help output and memory events are retained in `logs/`. This
is x86_64 compile/link and CLI-help evidence only. No HIP or SYCL accelerator
execution or performance result is claimed.

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

## Layer-0 parity-harness correction

After the layer-0 follow-up changed the parity utility to pass the requested
layer into `native_fmt`, the updated HIP utility compiled and linked on maestro1
with two jobs. The HIP `strata` target remained unchanged and its build check
completed; the SYCL `strata` target was also checked. Compiler temporaries were
placed under the prepared `/dev/shm/phase5-q8-selector-maestro1/tmp` directory
after maestro1's root filesystem filled during an initial attempt. The retry
passed. Updated command output is in `logs/hip-layer0-followup.txt` and
`logs/sycl-layer0-followup.txt`.

The HIP `strata --help` command exited 0. The SYCL binary could not complete
`--help`: its startup requested a SYCL device, but maestro1 exposed none and
aborted with `No device of requested type available`. This is recorded as an
unsupported CLI/runtime check, not a build failure or accelerator test. The
updated HIP parity binary SHA256 is
`1373edf7dad1b6e4420779cfe7516deca60e210695b1412307f6ef33c98f67ec`; HIP
`strata` remains `521b28649aae4cb09e8f4848be78a760f954a452ecfa9681e36afeb5ff981664`
and SYCL `strata` remains
`d624dce6c9094bacec584c1e6c0d2546973a3d436803ad00e267df69f5bc870c`.
The transferred source hashes are refreshed in `source-sha256.txt`.

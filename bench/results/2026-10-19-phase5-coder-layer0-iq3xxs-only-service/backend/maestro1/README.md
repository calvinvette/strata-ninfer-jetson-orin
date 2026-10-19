# maestro1 HIP/SYCL rebuild — 2026-10-19

The exact tracked source at commit `c5f9f319` (including the Q8_1 format-pair
selector change) was rebuilt on maestro1 from an isolated source snapshot. The
snapshot build completed HIP and SYCL configuration, compilation and linking;
both resulting `strata --help` commands exited 0. Build output, configure output,
help output, binary hashes, and cgroup events are retained in `logs/`.

The source manifest covers 880 files and is checked in
`logs/source-manifest.sha256`. 876 files matched the commit byte for byte; four
Windows batch files differed only in CRLF versus LF line endings, and none is
part of the HIP or SYCL build. All other manifest entries matched. HIP targeted
`gfx1100`; the SYCL build used the installed oneAPI 2026.1 toolchain. The exact
build script is `build.sh`.

The build scope was limited to 1.5 GiB and ran two jobs. Its final
`memory.events` reports `oom 0`, `oom_kill 0`, and `oom_group_kill 0`; `max 171`
records reclaim/limit events during the build and is retained as observed.
SYCL completed all 123 Ninja steps; HIP completed its target build and linked
both `strata` and `native_expert_parity`. Warnings from the installed ROCm,
oneAPI and SYCL compatibility headers were emitted, but neither backend build
failed.

maestro1 is x86_64 and has no qualified accelerator runtime for this test. This
is compile/link and CLI-startup evidence only; it is not HIP/SYCL GPU execution,
Orin performance evidence, or model execution. The Orin CUDA tests and runtime
results remain the evidence for runtime behavior.

The output binary hashes are in `logs/hip-binaries.sha256` and
`logs/sycl-binary.sha256`.

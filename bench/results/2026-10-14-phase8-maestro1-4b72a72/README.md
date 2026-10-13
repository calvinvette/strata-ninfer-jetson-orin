# Phase 8 HIP and SYCL build matrix — maestro1

Clean compile/link checks used the committed source at
`4b72a72b1b08d31a1d8859bf4c8d42a9c2e024e6` in an isolated snapshot on
maestro1. The snapshot contains tracked build inputs only; downloaded models
and binaries stayed on their original hosts. All 782 source files in
`source/source-sha256.txt` matched the committed checkout and were verified on
maestro1 before the builds.

| Backend | Configuration | Build result | Binary SHA256 |
| --- | --- | --- | --- |
| HIP | Release, gfx1100, CUDA disabled, tests disabled in CMake configuration, conversation tests enabled, prefill MMQ enabled | Pass, 313/313 steps | `f86810ec9f538af10a9b5bd6821b1631488c687c8ca2041e6e17ecef40238391` |
| SYCL | Release, oneAPI DPC++ 2026.1.1, parity option off | Pass, 123/123 steps | `2ac6e870c993742ee4435ff301ae7a5990e702c3a8405df3ad21ccdbc1136a47` |

Both builds used one job on a four-core x86_64 host with 3.7 GiB physical RAM.
The HIP build includes its configured parity/tool targets; neither build ran
tests, used an accelerator, loaded a model, or measured performance. maestro1
provides compile/link evidence only. Compiler warnings were present, including
GCC selection, unused/deprecation warnings, and oneAPI environment setup
notices; no configure, compile, or link errors remained in the completed runs.

Toolchain identities: Ubuntu 22.04 x86_64; GCC 11.4; ROCm SDK
`7.10.0a20251120`; AMD Clang `22.0.0git` (patched ROCm LLVM); Intel oneAPI
DPC++/C++ `2026.1.1.20260724`; CMake 3.31.10; Ninja 1.13.2. The HIP target
was configured for gfx1100, which does not imply runtime support on maestro1.

The reproducible build wrapper is
[build-phase8-maestro1.sh](../../../build/integration/build-phase8-maestro1.sh).
To repeat with a fresh committed source snapshot on maestro1, set `TRACE_ROOT`
to a directory containing `source/` and run that script. It writes
configure/build logs and binary hashes under `TRACE_ROOT/logs/`, and uses one
compile job.

After both links completed, each binary's `--help` command exited zero. The
captured output is in `logs/hip-help.txt` and `logs/sycl-help.txt`; these are
CLI launch checks only and did not initialize or exercise an accelerator.

The retained logs contain configure/build output and binary hashes. The first
two configure attempts stopped before compilation because the isolated
snapshot initially omitted `tests/hip` and then `tools/hip`; the final snapshot
included both. These snapshot-assembly retries are recorded in
`snapshot-retries.md` and are not backend build failures.

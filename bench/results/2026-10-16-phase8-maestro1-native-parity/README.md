# maestro1 HIP rebuild of native expert parity utility — 2026-10-16

The `native_expert_parity` utility was rebuilt on `maestro1` after its
`--dump-f32-dir` option was added. The build linked successfully and the
no-argument usage path printed the new option. This is x86_64 HIP compile/link
and CLI evidence only; it does not test an AMD GPU, run a model, or establish a
full current-source HIP build.

The isolated source tree began with the retained Phase 8 MTP-reset snapshot
(based on `eee15abe`, with the three MTP-reset files from `2b6dc076`). The only
replacement for this targeted check was
`src/kernels/native_expert_parity.cpp` from commit `9b6ed99e`, SHA256
`8a05cc45f3e65a2ad082b4b60aae41c5d99ebca5dbd98a3e993fedff5c45bbb2`. The
utility's existing CUDA/HIP dependencies were compiled and linked from that
snapshot in a fresh Release build directory; other changes in the current
checkout were not included. The source and build stayed under
`~/workspace/strata-validation/integration/native-parity-20261016/` on
maestro1. No model or build products were copied into Git.

The toolchain was ROCm SDK `7.10.0a20251120`, AMD clang `22.0.0git`, CMake
`3.31.10`, Ninja `1.13.2`, targeting `gfx1100`. HIP was enabled and CUDA
disabled. Configure and build used one job. The HIP target completed with
exit status zero; the retained log ends with successful linking at step 93/94
(the unused final Ninja step was not emitted). Compiler warnings were present;
no compile or link error was recorded. The binary SHA256 is
`07b990fc5c138b7b1b942a7f67e6f875fa7dbc73619ff73c1651a9197a1c199c`.

Running the binary with no arguments returned the expected usage status `2`
and printed `--dump-f32-dir`. Output, full configure/build logs, host/compiler versions, source hash and
binary identity are retained under `logs/`. The usage check does not exercise the
HIP device runtime.

Reproduce the build from the isolated source tree with the configure settings
in `logs/hip-configure.txt`, then:

```sh
cmake --build build-hip --target native_expert_parity --parallel 1
build-hip/native_expert_parity
```

The second command prints usage and exits with status 2. The separate current
Orin CUDA regression evidence and maestro1 full HIP/SYCL builds remain listed
in [integration status](../../../docs/integration/STATUS.md).

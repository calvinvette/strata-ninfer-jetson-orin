# maestro1 HIP build of the native-pack format guard — 2026-10-16

The `src/program/generate.cpp` guard from repository commit
`b2cde9b41b4eab1179a24d80133fc5a236560acb` compiled and linked into the HIP
`strata` service on maestro1. The target returned success and `strata --help`
returned 0 with `--expert-cache-cpu-order` present. The HIP executable SHA256
is in `binary.sha256`; complete build and help output are retained beside this
report.

The host build used the existing one-job HIP/GFX1100 configuration, AMD clang
22 with the pinned GCC 11 headers, and the current integration source snapshot
at `e6a55b30f596ecc5173d2eb55a4087662b7ee88f`. The only overlaid source file
was `generate.cpp` (SHA256
`bdd9ea049d9cdbb0cf119cb7baf601638796c6d5d12fc838793ad134004a2c19`), which
contains the format guard; all other source files and the build configuration
were unchanged. The original `generate.cpp` was restored after the build and
its SHA256 matched the retained snapshot. The resulting executable is
compile/CLI evidence only: maestro1 has no qualified HIP device for runtime
testing.

The separate SYCL project compiles `sycl/src/program/generate.cpp`; it does
not consume the modified CUDA/HIP source file, so this change does not affect
the SYCL target.

The incremental build command was:

```sh
cmake --build \
  /mnt/sda2/home/calvin/workspace/strata-validation/integration/current-e6a55b30-hip-final/build \
  --target strata -j1
```

For the CLI check, the installed ROCm devel and gfx110X library directories
were added to `LD_LIBRARY_PATH` before invoking the resulting `strata --help`.

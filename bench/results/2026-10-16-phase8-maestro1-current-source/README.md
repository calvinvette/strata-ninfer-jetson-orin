# Current-source HIP build on maestro1 — 2026-10-16

A clean sparse checkout at source commit `e6a55b30f596ecc5173d2eb55a4087662b7ee88f` completed a full current-source HIP build on maestro1. Both `strata` and `native_expert_parity` linked. The no-argument parity utility returned its expected usage status 2 and included `--dump-f32-dir`; `strata --help` returned successfully. The exact build and CLI output is retained under `logs/hip/`.

The host is x86_64 and has no usable AMD GPU runtime. This is compile/link and CLI evidence only; it does not qualify HIP GPU execution, model behavior, or Orin performance. The CMake configure log notes that pack-dependent expert arena and optional IQ parity tests were not registered because their local fixtures/dependencies were absent. No tests are claimed by this build.

Configuration used Release, HIP enabled for `gfx1100`, CUDA disabled, tests disabled, one build job, CMake 3.31.10, Ninja 1.13.2, AMD clang 22.0.0git, and the pinned llama.cpp checkout listed in `logs/host-toolchain.txt`. The compiler emitted warnings; the build exited successfully with no compile or link errors. Binary hashes are in `logs/hip/binaries.sha256`.

Reproduce from a clean checkout of the recorded source revision with the configure values in `logs/hip/configure.txt`, then build `strata` and `native_expert_parity` with one job. This report is limited to the exact revision and targets recorded here.

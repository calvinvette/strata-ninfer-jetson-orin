# HIP shared/combined MoE diagnostic rebuild — maestro1 — 2026-10-20

The expanded opt-in shared/combined MoE output capture was rebuilt with two
jobs in the staged maestro1 HIP/SYCL trees. HIP recompiled the changed
`src/core/verify.cpp`, relinked the configured targets, and `strata --help`
exited 0. The updated binary hashes are in `hip-binaries.sha256`.

The SYCL project resolves verifier code from its separate
`sycl/src/core/verify.cpp` and `sycl/include/strata/core/verify.hpp` overlay;
these diagnostic changes are CUDA/HIP-specific, so its incremental build
reported no work and its `--help` exited 0. This is x86 compile/CLI evidence,
not accelerator runtime or performance evidence. Existing HIP API
`nodiscard` warnings remain; no build errors occurred. Cgroup `memory.events`
recorded zero low/high/max/OOM/OOM-kill events.

`source-sha256.txt` records the exact Orin verifier source inputs copied to
maestro1. Configure/build logs, binary hashes, CLI output and toolchain details
are retained here.

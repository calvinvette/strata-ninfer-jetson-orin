# HIP position-filtered GDN diagnostic rebuild — maestro1 — 2026-10-20

The opt-in verifier GDN position filter was rebuilt with two jobs in the staged
maestro1 HIP/SYCL trees. HIP recompiled `src/core/verify.cpp`, relinked the
configured targets, and `strata --help` exited 0. Binary hashes are retained in
`hip-binaries.sha256`.

The SYCL project uses its separate `sycl/src/core/verify.cpp` and
`sycl/include/strata/core/verify.hpp` overlay. It does not include this
CUDA/HIP graph diagnostic, so the incremental SYCL build reported no work and
`strata --help` exited 0. These are x86 compile/CLI checks only, with no
accelerator runtime claim. Existing HIP API `nodiscard` warnings remain; no
build errors occurred. Cgroup `memory.events` recorded zero
low/high/max/OOM/OOM-kill events.

`source-sha256.txt` records the exact Orin verifier source inputs copied to
maestro1. Configure/build logs, binary hashes, CLI output and toolchain details
are retained in this directory.

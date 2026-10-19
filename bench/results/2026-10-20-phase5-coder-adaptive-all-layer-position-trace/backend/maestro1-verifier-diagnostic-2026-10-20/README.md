# HIP verifier diagnostic rebuild — maestro1 — 2026-10-20

The opt-in verifier diagnostic change was rebuilt in the staged maestro1
HIP/SYCL trees with two jobs. The top-level `src/core/verify.cpp` and
`include/strata/core/verify.hpp` were copied individually and their hashes were
checked against Orin before building. HIP recompiled `verify.cpp`, relinked
`strata` and the configured HIP targets, and `strata --help` exited 0. Its
`strata` binary hash is in `hip-binaries.sha256`.

The SYCL project resolves its verifier from `sycl/src/core/verify.cpp` and its
header from `sycl/include/strata/core/verify.hpp`. Those overlay files do not
contain this CUDA/HIP-only graph capture diagnostic and were unchanged; the
SYCL build reported no work and its `--help` exited 0. This is compile/CLI
portability evidence on maestro1, not accelerator runtime or Orin performance
evidence. The compiler emitted existing HIP API `nodiscard` warnings; no build
errors occurred. Cgroup `memory.events` remained zero.

The exact hashes of the two copied top-level source inputs are in
`source-sha256.txt`. Configure/build logs, binary hashes, CLI output, and
memory-event counters are retained in this directory. maestro1 uses the same
staged source/toolchain tree documented in the adjacent
`maestro1-current-source-2026-10-19` backend report.

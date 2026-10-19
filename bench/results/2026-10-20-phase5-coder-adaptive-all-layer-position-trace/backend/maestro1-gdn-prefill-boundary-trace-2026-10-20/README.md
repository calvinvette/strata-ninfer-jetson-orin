# maestro1 HIP/SYCL build — GDN prefill boundary trace — 2026-10-20

The source manifest matches the exact local hashes of `src/prefill/prefill.cpp`,
`src/core/verify.cpp` and `include/strata/core/verify.hpp`. HIP rebuilt and
linked the changed prefill source and the current `strata` binary. The SYCL
incremental build reported no work; the active SYCL overlay was not changed by
this diagnostic. Both `strata --help` checks exited 0. Build memory event
counters were zero. The target is maestro1 x86_64, so this is compile/link and
CLI evidence only; no Orin performance or accelerator runtime result is claimed.

See the retained build logs, exact source hashes,
binary hashes, help outputs and memory event counters in this directory.

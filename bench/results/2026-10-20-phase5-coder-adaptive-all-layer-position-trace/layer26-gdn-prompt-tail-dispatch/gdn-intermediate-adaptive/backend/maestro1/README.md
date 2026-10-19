# GDN multi-position diagnostic backend check — maestro1 — 2026-10-20

The staged source inputs match the local `src/core/verify.cpp` and
`include/strata/core/verify.hpp` SHA-256 values in `source-sha256.txt`. The
HIP build compiled the changed verifier and the dependent `generate.cpp`,
linked `strata`, and passed `strata --help` (exit 0). The build used two jobs.

The SYCL build uses its separate verifier source/header overlay. Those files
were unchanged; its incremental build reported no work and `strata --help`
exited 0. Cgroup low/high/max/OOM/OOM-kill counters were zero. These checks are
x86_64 compile/link and CLI evidence only; no HIP or SYCL accelerator runtime
execution occurred on maestro1.

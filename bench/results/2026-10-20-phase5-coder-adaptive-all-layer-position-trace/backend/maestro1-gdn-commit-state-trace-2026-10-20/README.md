# maestro1 HIP/SYCL build — GDN accepted-commit trace — 2026-10-20

The build used the exact current `src/core/verify.cpp`,
`include/strata/core/verify.hpp` and `src/prefill/prefill.cpp` hashes listed in
`source-manifest.sha256`; `local-source-sha256.txt` confirms they match this
checkout. HIP rebuilt the verifier and dependent binaries, then linked `strata`.
The HIP `strata --help` check exited 0. The separate SYCL overlay had no changed
inputs, so its incremental build reported no work; its `strata --help` check
exited 0. The SYCL overlay does not contain this CUDA/HIP verifier diagnostic.
Build cgroup memory event counters were zero.

maestro1 is x86_64. These are compile/link and CLI checks only; no accelerator
runtime or Orin performance result is claimed. Build logs, binary hashes, exact
source manifests, help output and memory event counters are retained here.

# Backend build evidence

The Orin CUDA candidate rebuilt with one job. A 28-GiB supervised focused CTest
selection passed six route-window, verifier, native multi, and Q8_1 expert tests;
see `../cuda-focused-ctest/` for logs and telemetry.

The changed verifier/header and its current dependent service sources were
synchronized to maestro1 and rebuilt as a complete HIP service with one job.
The service linked for gfx1100, and `strata --help` exited 0 with the ROCm
shared-library path configured. The machine-readable identities and raw build
log are retained here. maestro1 is x86_64 build and CLI evidence only; no HIP
GPU or model execution was run.

SYCL's CMake source resolver selects `sycl/src/core/verify.cpp` and
`sycl/include/strata/core/verify.hpp` when present. This opt-in CUDA/HIP route
capture was added to the native source pair; the migrated SYCL files were not
changed by this work.

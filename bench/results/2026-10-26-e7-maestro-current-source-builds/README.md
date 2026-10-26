# Current-source HIP and SYCL builds on maestro1

Date: 2026-10-26. Source commit: `1f9f116b181ef0503f4203f26922b90e213d4615`.

## Result

Both configured backend builds completed successfully against the current
NInfer integration source, and each resulting `strata` binary completed a
model-free `--help` invocation. This is x86_64 compile/link and CLI startup
evidence only. maestro1 has an Intel HD Graphics 500; neither HIP nor SYCL GPU
execution, Orin performance, nor accelerator correctness was tested.

| Backend | Compiler/configuration | Build | `strata --help` | `strata` SHA256 |
| --- | --- | --- | --- | --- |
| HIP | ROCm HIP 7.2.53210; AMD Clang 22.0.0; Release; `gfx1100`; `STRATA_PREFILL_MMQ=ON`; build parallelism 2 | Passed | Passed | `dcb805d33e2869aa3a96a6acc9b64369470d6ca17a9b5cbbb98851c1c115a33f` |
| SYCL | Intel oneAPI DPC++/C++ 2026.1.1; Release; `STRATA_SYCL_PARITY=ON`; GCC 11 install-dir compatibility flags; build parallelism 2 | Passed (201/201 steps) | Passed | `c15242e071d781201d5f4c767a79315e2f43c9bd39482655750dd3993e99344f` |

The source checkout was a depth-1 clone of `feat/ninfer-expert-e0` at the
commit above. Both builds used the pinned ggml dependency at
`llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d`. Build trees and
toolchains remain on maestro1's `/mnt/sda2`; no binaries, models, or toolchains
were copied into this repository. The complete configure/build output and
help captures are in [`evidence/`](evidence/).

The SYCL help invocation used the installed oneAPI environment. Starting the
binary without that environment fails to load `libmkl_sycl_blas.so.6`; the
runtime environment is therefore part of this build's launch requirements.
The oneAPI setup printed environment warnings about `hwloc` and UMF setup, but
the build and help check succeeded. CMake did not register two optional HIP
tests because the model expert arena and Python NumPy/vendored gguf-py fixture
dependencies were absent. No test executable or device test was run.

## Reproduction locations

Remote build root: `/mnt/sda2/tmp/calvin/strata-ninfer-build-e0-1f9f116b/`.
The CMake cache and full build logs are retained there. Builds used
`cmake --build ... --parallel 2`; the exact configure output and compiler
metadata are preserved in this report's evidence bundle.

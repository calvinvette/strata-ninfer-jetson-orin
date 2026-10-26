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

## 2026-10-26 follow-up on state-diagnostic source

After adding opt-in final-state fingerprints, both backend builds were
repeated from exact source commit
`68de59ab2c6736ca328c83afabe2138123cd7051`. The HIP target built and
`strata --help` exited 0 with ROCm libraries on `LD_LIBRARY_PATH`. The SYCL
target first stopped at generated DPCT BLAS code because the oneMKL environment
was not sourced (`MKLROOT` was unset). Sourcing both the oneAPI compiler and
oneMKL `env/vars.sh` files allowed the remaining seven build steps to finish.
The resulting SYCL binary compiled and linked, but this host reports “No
platforms found” from `sycl-ls`; its `strata --help` startup aborted because no
SYCL device was available. Record this as SYCL compile/link evidence only, not
CLI startup or runtime qualification.

| Backend | Exact source | Build | CLI help | Binary SHA256 |
| --- | --- | --- | --- | --- |
| HIP | `68de59ab2c6736ca328c83afabe2138123cd7051` | Passed, two jobs | Passed, exit 0 | `a346ec5159dee31c382dae4513450c84b02a7ed457ac5cca4ee9dee64b1b9a05` |
| SYCL | `68de59ab2c6736ca328c83afabe2138123cd7051` | Passed after setting `MKLROOT`, two jobs | Unsupported here: no SYCL platform/device | `2099aa4e33662a6894e01fd736d3a19127f7dd99bf80a0aa9421e50e99b399d9` |

Both binaries remain on maestro1. No accelerator execution or Orin performance
was measured. The previous-source evidence above remains valid for commit
`1f9f116b181ef0503f4203f26922b90e213d4615`; it must not be treated as
help/runtime evidence for this newer source commit.

## 2026-10-26 follow-up on the Q2_0 CPU arithmetic mirror

The HIP and SYCL Release build trees were incrementally rebuilt at exact
source commit `44db548402b193202703256da81d75720312cc8d`, with parallelism 2.
Both rebuilt the changed `src/kernels/cpu/native_expert.cpp` and linked their
configured targets successfully. HIP `strata --help` passed after adding the
installed ROCm libraries to `LD_LIBRARY_PATH`. Its binary SHA256 is
`329331de34fc6eba6132996ec5be96aa545a61a28b1c87b602972fbe02f65efa`.

SYCL compiled and linked all six remaining steps after sourcing the installed
oneAPI compiler and oneMKL environments. The resulting binary SHA256 is
`a966bc9df42f15b40ea80ff5a25e7262c91a3005fd42899668b91d46f38baa10`.
`strata --help` aborted with “No device of requested type available,” and
`sycl-ls` reported no platforms. This is compile/link evidence only for SYCL,
not CLI startup or runtime qualification. maestro1 provides x86_64 portability
evidence only; no HIP/SYCL accelerator execution or Orin performance was
measured. Build output, help output and hashes are in
[`evidence/current-source-44db5484/`](evidence/current-source-44db5484/).

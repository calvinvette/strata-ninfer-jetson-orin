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

## 2026-10-26 follow-up on expert-ID-filtered Q8_1 arithmetic

The `strata` and `native_expert_parity` targets rebuilt at exact source commit
`6b419221a0d712d18685b19df27e059fc455841f` on maestro1 with parallelism 1.
HIP build/link, `strata --help`, and the Q8_1 selector contract all passed. The
SYCL targets also built and linked after sourcing the oneMKL environment for
the final links. maestro1 has no SYCL device, so `strata --help` could not
start; the separate SYCL parity program does not implement the selector
contract mode. These are x86_64 compile/link checks only. See the [exact-source
report and logs](evidence/current-source-6b419221/README.md).

## 2026-10-26 follow-up on model-layer GDN replay

After generalizing `gdn_parity` to replay a selected model layer, maestro1
rebuilt and linked the HIP target at `32f04b5695fe9aa6afa540f1b84114a3d17a11fa`
with parallelism 1. The HIP runtime self-test stopped before kernel cases
because the host reported no ROCm-capable device. This is compile/link
evidence only; the new replay was exercised on Orin CUDA. See the [build
record](evidence/current-source-32f04b56-gdn-parity/README.md).

## 2026-10-26 follow-up on position-filtered QSA capture

The complete `strata` target was rebuilt from exact source commit
`03806747172378e9eb5a99a2a2194c655675b236` in an isolated checkout on
maestro1. HIP used ROCm HIP 7.2.53210 / AMD Clang 22.0.0, Release, gfx1100,
and one build job. SYCL used Intel oneAPI DPC++ 2026.1.1 with oneMKL 2026.1,
Release, and one build job. Both used the pinned ggml source
`llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d`. The HIP build and
model-free `strata --help` passed. The SYCL build and link passed; its
`strata --help` invocation aborted with exit 134 because maestro1 exposes no
SYCL device (`No device of requested type available`). This is x86_64
compile/link evidence only. No HIP or SYCL accelerator execution and no Orin
performance measurement was made.

| Backend | Build | CLI help | Binary SHA256 |
| --- | --- | --- | --- |
| HIP | Passed, one job | Passed | `09b274818ce99f098cd9af18fe2873cd94f0a82189c45155cd6dca6fe432c289` |
| SYCL | Passed, one job | Unsupported here: no SYCL device (exit 134) | `aa99a12fc329328e8e1c43bc10b1cb26e6819a5cc0bcd188e5323f4ab90419f0` |

Build root on maestro1: `/mnt/sda2/tmp/calvin/strata-ninfer-build-e0-03806747/`.
The exact configure, build, help and hash logs remain there under `logs/`;
the compiler executable was `build-sycl/sycl/strata` (CMake places it in the
backend subdirectory). The checkout, toolchains, and binaries were not copied
into this repository. maestro1 provides no Orin performance or AMD/SYCL
runtime qualification.

## 2026-10-26 follow-up on residual-boundary capture telemetry

After adding opt-in missing-capture telemetry, the current checkout was
rebuilt on maestro1 at exact source commit
`db95a63c874fa0a7cfc9cff450696cd3a9083990`, using one build job. The HIP
target rebuilt the modified verifier, linked `strata_engine`, compiled the
final executable, and linked successfully. HIP `strata --help` exited 0 with
the installed ROCm libraries on `LD_LIBRARY_PATH`. The SYCL build target
completed successfully; its source tree is separate (`src/sycl` and
`sycl/include`) and contains no corresponding change from this commit, so the
target was already up to date. With the installed oneAPI compiler and oneMKL
environment sourced, SYCL `strata --help` also exited 0. maestro1 is x86_64
build evidence only; no accelerator was exercised.

| Backend | Source handling | Build target | `--help` | SHA256 |
| --- | --- | --- | --- | --- |
| HIP | Recompiled modified `src/core/verify.cpp`, linked engine and executable | Passed, one job | Passed, exit 0 | `c8cf5e49bc69970bb259767cc1650556c442506278d34cd11ee2ee24e46dac43` |
| SYCL | Separate SYCL source tree unchanged; target up to date | Passed | Passed with oneAPI/oneMKL environment, exit 0 | `aa99a12fc329328e8e1c43bc10b1cb26e6819a5cc0bcd188e5323f4ab90419f0` |

The same commit's CUDA binary was rebuilt on Orin and used for the third
paired layer-0 / layer-1 localization capture. Its SHA256 was
`41def6adbd54d4f1dd8e20e4f50ff685ea0248cd3ddb24e36ad0fe1128443051`.
That paired diagnostic run failed the persistent-state gate and is not a
performance result. The capture telemetry interpretation and limits are in
the [E6 layer-boundary report](../2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#capture-path-telemetry-follow-up).

## 2026-10-26 follow-up on multirow residual-boundary capture

After adding ordinary-verifier multirow boundary capture, maestro1 fetched
exact source commit `8ead1358d27b8f8e23c9ac689d62e0d694a373ae`. The HIP target
recompiled `src/core/verify.cpp`, linked `strata_engine`, rebuilt the final
executable and passed `strata --help` (exit 0) with ROCm libraries configured
in `LD_LIBRARY_PATH`. The SYCL target completed successfully and was already
up to date because its separate source tree was not changed; with oneAPI and
oneMKL initialized, its `strata --help` also exited 0. This is compile and
model-free startup evidence on x86_64 only; no HIP/SYCL device execution was
available.

| Backend | Source handling | Build target | `--help` | SHA256 |
| --- | --- | --- | --- | --- |
| HIP | Recompiled multirow capture code and relinked executable | Passed, one job | Passed, exit 0 | `bf86fb2863acd779aabcd7fdc075a9047f8707e8e9f09fbfa1ff1513246f650c` |
| SYCL | Separate SYCL tree unchanged; target up to date | Passed | Passed with oneAPI/oneMKL environment, exit 0 | `aa99a12fc329328e8e1c43bc10b1cb26e6819a5cc0bcd188e5323f4ab90419f0` |

The current Orin CUDA binary from this source had SHA256
`54b89b408ab41350561fc0f920030187a854e7339bd23f9c02a1ef92cc895fc5` and
emitted the layer-0 / position-2043 captures in both arms. The comparison is
documented in the [E6 boundary report](../2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#multirow-ordinary-verifier-boundary-capture).

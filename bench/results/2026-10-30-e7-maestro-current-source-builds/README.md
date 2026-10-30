# Current-source HIP and SYCL rebuild on maestro1

Date: 2026-10-30  
Source: `feat/ninfer-expert-e0` at `4229c00ec9bbe04c62c92d2e907c6aeed9679a38`  
Host: maestro1 x86_64; build parallelism: 1  
Scratch: `/mnt/sda2` (55 GiB free after the builds); root filesystem remains nearly full.

## Results

Both configured backend trees rebuilt the complete default target set against
the current source. The HIP `strata` binary passed `--help`. A model-free
host-only CTest, `shared_memory_budget_test`, passed in 0.05 seconds. The SYCL
tree compiled and linked all targets after sourcing both the Intel oneAPI
compiler and oneMKL environments. Its `--help` invocation aborted because
maestro1 exposes no SYCL device. No accelerator test ran on this host.

| Backend | Toolchain | Build | CLI/help | SHA256 |
| --- | --- | --- | --- | --- |
| HIP | ROCm HIP 7.2.53210 / AMD Clang 22.0.0, `gfx1100` | Passed, one job | Passed, exit 0 | `f2c908f676e6d780f414de669f72c936bb38ffa3c5d33983487857adb49ede29` |
| SYCL | Intel oneAPI DPC++ 2026.1.1 / oneMKL 2026.1 | Passed, one job; first link attempt failed before oneMKL setup, then passed with it | Unsupported: aborts with “No device of requested type available” | `dad182e8e6c278a3a6fc278817b26623e17137f629a4a2dff91ca23aeb6aefa85e` |

This is x86_64 portability evidence only. It does not establish HIP/SYCL device
execution, accelerator correctness, or Orin performance. The one-host CTest
only checks the shared-memory budget contract.

## Reproduction and retained logs

Build trees and logs remain on maestro1 under
`/mnt/sda2/tmp/calvin/strata-ninfer-build-e0-03806747/`. The source worktree
there is detached at the source commit above. Build logs are
`logs/hip-build-4229c00e.log` and
`logs/sycl-build-4229c00e-onemkl.log`. The failed first SYCL link is retained
as `logs/sycl-build-4229c00e.log`; it failed only because the oneMKL variables
were not loaded. CLI logs are `logs/hip-help-4229c00e.log` and
`logs/sycl-help-4229c00e.log`. No build products or toolchains were copied into
the repository.

## 2026-10-30 follow-up: request-tagged route trace change

The shared C++ change at `d321286f` was rebuilt on the same maestro1 source
worktree and configured trees, with one build job. Both backend build commands
passed. The HIP `strata --help` check passed after adding the ROCm development
library directory to `LD_LIBRARY_PATH`; `shared_memory_budget_test` passed
again. The SYCL `strata` target built and linked. With the compiler and oneMKL
environment scripts sourced, its `--help` invocation reached runtime and
aborted because maestro1 has no SYCL device. No accelerator runtime test was
performed.

| Backend | Build | CLI/help | SHA256 |
| --- | --- | --- | --- |
| HIP | Passed, one job | Passed, exit 0 | `ce9f653d5bf60ec0f0dae2561bada509d11f54d741d725b0ac279b2c5017cbf0` |
| SYCL | Passed, one job | Unsupported: no SYCL device | `dad18286e8a2a3a6fc278817b26623e17137f629a4a2dff91ca23aeb6aefa85e` |

The HIP log is `logs/hip-build-d321286f.log`; the SYCL full build log is
`logs/sycl-build-d321286f.log` and its explicit service-target build log is
`logs/sycl-strata-d321286f.log`. The exact-source binaries and logs remain on
maestro1 under `/mnt/sda2/tmp/calvin/strata-ninfer-build-e0-03806747/`.
This follow-up is x86 compile/link and HIP startup evidence only; it says
nothing about Orin performance or SYCL device execution.

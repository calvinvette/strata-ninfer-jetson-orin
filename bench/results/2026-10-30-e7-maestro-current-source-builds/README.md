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

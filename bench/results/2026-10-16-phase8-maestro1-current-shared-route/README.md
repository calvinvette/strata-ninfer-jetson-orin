# Current shared-source HIP and SYCL rebuilds — maestro1 — 2026-10-16

The existing maestro1 HIP and SYCL build trees were incrementally rebuilt
against the exact current repository revision `7dea072d300083bdcdff4cc4ed6d862746626d4e`.
That revision changed four build/source files since the prior complete builds at
`e6a55b30f596ecc5173d2eb55a4087662b7ee88f`:

- `CMakeLists.txt`
- `src/kernels/cpu/native_expert.cpp`
- `src/kernels/native_expert_parity.cpp`
- `src/program/generate.cpp`

The prior build trees had completed at the baseline revision. At the current
revision, the HIP build reconfigured and rebuilt `strata` and
`native_expert_parity` with one job. Both targets linked; `strata --help`
returned 0 and the parity tool's no-argument usage returned its expected status
2. The logs record successful completion and binary hashes.

The separate SYCL build recompiled the shared CPU expert implementation and
linked `strata` successfully with one job. oneMKL was installed outside the
default linker search path, so the final link used an explicit `-L` path to its
installed library directory. Compiler temporary files were directed to
`/mnt/sda2` because maestro1's root filesystem was full. `sycl-ls` reported no
platforms, and invoking `strata --help` consequently aborted while the SYCL
runtime searched for a device (exit 134). This is recorded as an unsupported
runtime/CLI cell, not a successful help check or an accelerator-runtime result.

The host was x86_64 maestro1. HIP targeted `gfx1100`; SYCL used Intel oneAPI
DPC++ 2026.1.1. The dependency checkout was llama.cpp
`3cf03257f219afbe7334045ff7c6a06ac68c627d`. Build parallelism was one because
the host has 3.7 GiB RAM. No device execution, model test, or Orin performance
claim follows from these results. The Orin CUDA regression evidence remains in
its separate report. Phase 8 remains open for its native runtime,
supported-profile, regression and rollback evidence.

`logs/hip/` and `logs/sycl/` retain build output, source identity, CLI/platform
checks and binary hashes. The SYCL logs also retain the initial failed link and
the successful link retry, so the required oneMKL link-path adjustment is
visible.

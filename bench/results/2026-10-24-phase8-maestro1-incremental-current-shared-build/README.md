# Current shared-source HIP and SYCL rebuild — maestro1 — 2026-10-24

This validates the shared C++ source changes after the full current-source
snapshot build recorded on 2026-10-23. That earlier build snapshot was
`d0baa266a37025bf873b3f01f26470c5c196bed1`; the current integration checkout
is `a0a18c27e053f13a7bf71d83af5b64565c4340c8`. Five shared files differ from
the earlier snapshot. Their SHA256 values are listed below and were checked in
the remote build input.

## Builds and checks

The earlier HIP and SYCL build trees were configured for maestro1's ROCm 22
`gfx1100` HIP toolchain and Intel oneAPI DPC++ 2026.1.1 x86 CPU SYCL toolchain.
Their build directories were retained, and the current five files were overlaid
on a separate remote validation source snapshot. Both configured builds ran
serially (`cmake --build ... --parallel 1`) and completed with exit status zero.
HIP rebuilt the affected CPU/native-expert, engine, pool, parity, and test
objects; SYCL rebuilt the corresponding shared CPU objects and relinked its
service and parity targets. The original `d0baa266` source files were restored
afterward. Current-source binaries and build logs remain on maestro1 under
`/mnt/sda2/home/calvin/workspace/strata-validation/phase8-current-source-a0a18c27/`.

- HIP `strata --help`: exit 0 with the ROCm runtime library path configured.
- HIP `shared_memory_budget_test`: 1/1 passed.
- HIP `native_expert_parity` no-argument usage path: printed its CLI usage and
  returned 2, as expected without a model argument. An attempted `--help` is
  not supported by this utility and was not counted as a test.
- SYCL `strata --help`: exit 0.
- SYCL `conversation_snapshot_test`: unavailable in this current environment;
  it reports that no device of the requested type is available. The prior
  3,901-check CPU-device result is documented separately and is not repeated
  here.

No HIP GPU or SYCL accelerator runtime was available or exercised. These are
x86_64 compile, link, CLI, and one host CTest results, not Orin performance
measurements. The root filesystem remained at 99%; build artifacts and logs
were kept on `/mnt/sda2` (85 GiB free at the start/end), not the root volume.

## Shared source identities

| File | SHA256 |
| --- | --- |
| `include/strata/kernels/cpu/native_expert.hpp` | `08096702f380c5f1c7f15c7c87aaf9c87b6b8526568744b9cd9bae543b779ffc` |
| `src/kernels/cpu/native_expert.cpp` | `a953a7df61b17612897ad71df6139f8870b180683300e6ee61a5da676fbd7ae0` |
| `src/kernels/cpu/pool.cpp` | `41c22c698f6c92449148eb70af3ab438b8354f012ae6aed92db407c6665d7a8a` |
| `src/kernels/gdn_parity.cpp` | `65706ec29b4e38a0fe5862db61507fe955df31418e82125ded3ad88f42a4aaf5` |
| `src/kernels/native_expert_parity.cpp` | `8eae93adf46655775dbdb9d41d9236dbf4178a472fcfbe2b4f293a523d582171` |

The full HIP build output records 59 compile/link actions plus its CMake/Ninja
setup status. The SYCL output records its 25 incremental steps. No source,
model, build product, or compiler log was added to Git from maestro1.

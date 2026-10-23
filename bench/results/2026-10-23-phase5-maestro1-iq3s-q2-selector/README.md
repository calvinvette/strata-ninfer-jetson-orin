# maestro1 HIP/SYCL selector rebuild — 2026-10-23

After adding the opt-in IQ3_S/Q2_0 CPU Q8_1 path, the shared sources were
refreshed in the existing isolated maestro1 source snapshot. All four changed
files matched the Orin checkout by SHA256:

| File | SHA256 |
| --- | --- |
| `CMakeLists.txt` | `dd114578c3609a39b8e06f4fe179116b82a9f598ca45d786bdd8f100f8bd3934` |
| `include/strata/kernels/cpu/native_expert.hpp` | `f796b7c76f41004aa3cd53e4acff1763461ff47f8cf4af2c563f64910b7c6efb` |
| `src/kernels/cpu/native_expert.cpp` | `3a1f4f3c227da665bd91e541d97cd2793539ce8f2a11385dde9d7df6b410fe83` |
| `src/kernels/native_expert_parity.cpp` | `16c1690227cb5b539fdd911450645743a97436dc4ffe054ae8ceee602d81eb80` |

The HIP Release tree rebuilt and linked `strata` and `native_expert_parity` with
one job. `strata --help` returned 0, and
`native_expert_parity --q8_1-selector-contract` passed. The SYCL Release tree
rebuilt and linked `strata` in 20/20 steps; `strata --help` returned 0 after
loading the oneAPI runtime. Existing HIP `nodiscard` and SYCL overlay unused-
helper warnings remain; neither build had compile or link errors.

| Artifact | SHA256 |
| --- | --- |
| HIP `strata` | `86f2631d764cee608cab01c3cad0456c741377bf9e5d6996dc98a800c3ca81ba` |
| HIP `native_expert_parity` | `a0b00e2442fe0a127afbb47f46713ecdee40bea99441fd9a7cafede0477f33a8` |
| SYCL `strata` | `06a8e272921c926e47dc0a6caaee99ca8a22d5e573ba3fb9be2692be9230504b` |

Builds used maestro1's x86_64 host and `/mnt/sda2` scratch volume. This is
compile/link, CLI-startup and CPU-only selector-contract evidence; neither a
HIP/SYCL accelerator nor a model was run. It is not Orin performance evidence.

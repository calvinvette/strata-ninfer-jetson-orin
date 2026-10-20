# maestro1 current-source HIP/SYCL rebuild — 2026-10-19

This is compile/link and CLI evidence for the opt-in CUDA-order Q8_1 CPU
activation producer and the updated expert parity harness. The active Git head
at build time was `d0b42f4bd497c410859feee5d9e116f96b0a0331`; the two changed
source files were copied into the existing isolated maestro1 validation stage
and their SHA256 values are recorded below. maestro1 is x86_64, so these runs
do not qualify Orin performance or execute either accelerator backend.

The bounded HIP build used ROCm/HIP 7.2.53210 for `gfx1100` with two jobs. The
`strata` target linked; with the toolchain's `_rocm_sdk_devel/lib`,
`_rocm_sdk_libraries_gfx110X_dgpu/lib` and `_rocm_sdk_core/lib` on
`LD_LIBRARY_PATH`, `strata --help` exited successfully. The changed
`native_expert_parity` target also linked. Its supported
`--q8_1-selector-contract` mode passed; this mode does not initialize a GPU.
The parity tool does not implement `--help`.

The SYCL build used Intel oneAPI DPC++ 2026.1.1, also with two jobs. It rebuilt
the top-level `src/kernels/cpu/native_expert.cpp` and linked `strata`; the
SYCL-specific `src/program/generate.cpp` overlay remained active. `strata
--help` exited successfully. The toolchain setup emitted its existing hwloc,
UMF environment and GCC include-directory warnings; there were no build or
link errors. No SYCL device execution was attempted.

Commands, tool versions, and SHA256 records:

```text
HIP: cmake --build build-hip --target strata --parallel 2
HIP parity: cmake --build build-hip --target native_expert_parity --parallel 2
SYCL: cmake --build build-sycl-iq3s --target strata --parallel 2
```

`hip-strata-build.txt`, `hip-parity-build.txt` and `sycl-strata-build.txt`
retain full build output. The corresponding help and selector-contract output
is retained beside them. Binary hashes:

```text
2bca22e72ef6f451ecca74dfb72efaeaa480bae76d1da10ef2ab9586201e9b32  HIP strata
f963a39f0faf3d20db70058a06da3fd4f58a34c5d6dab1a29589cf9872c1fb26  HIP native_expert_parity
b58646deb030371db53ea14e2e1937465ea0138ec07233f9869f91890c0c3c8f  SYCL strata
```

The consumed source hashes were:

```text
ba4321ba35bb96de893288a08411e68fe361517a763f605d140831c45a78dc3e  src/kernels/cpu/native_expert.cpp
96e98e795c311239751424afcc4ff663417aaea92d1ea6eefe28d10a74396730  src/kernels/native_expert_parity.cpp
5464e78e760607baa25b0688e31d1e249ef953f55456c22aa4dc91f265a51951  sycl/src/program/generate.cpp overlay
```

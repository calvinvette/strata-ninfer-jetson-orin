# Full current-source HIP and SYCL builds — maestro1 — 2026-10-23

Fresh isolated Release builds of the full current Strata source snapshot
completed for HIP and SYCL on maestro1 (`x86_64`, Ubuntu 22.04, Linux 6.8).
The snapshot is commit `d0baa266a37025bf873b3f01f26470c5c196bed1`; the later
repo commits through `c70998f7` changed docs, Python probe code and result
records only. `git diff --quiet d0baa266..HEAD -- src include sycl` passed,
so the shared backend sources at the current HEAD match those compiled here.

Both builds used one job because maestro1 has 3.7 GiB RAM and 4 GiB swap.
Build output and temporary files were kept on `/mnt/sda2` (85 GiB free at
completion); the nearly full root filesystem was not used for build output.
Compressed full build logs, configure logs, host/compiler metadata, binary
hashes, `ldd` output and smoke outputs are retained in this directory.

## HIP

The Release HIP build completed all 345 Ninja targets. It used ROCm/AMD Clang
22.0.0, HIP platform `amd`, target `gfx1100`, `STRATA_ENABLE_HIP=ON`,
`STRATA_ENABLE_SYCL=OFF`, `STRATA_BUILD_TESTS=ON`, and
`STRATA_PREFILL_MMQ=ON`. The GGML HIP/CUDA backends were off; this built
Strata's HIP path. `strata --help` returned 0; the binary hash is in
[`tests/hip-binary-sha256.txt`](tests/hip-binary-sha256.txt).

The selected HIP CTest run had one actual pass:
`shared_memory_budget_test` (10 cases). `q8_oracle_contract_test`,
`q2_portable_reference_test` and `expert_multi_test` were skipped by their
guards; `q2_portable_reference_test` reported that AVX512 was unavailable,
`expert_multi_test` listed missing AVX512F/BW/VL/VNNI/VBMI CPU features, and
the Q8 test emitted no skip reason. These skips are not counted as passes.

## SYCL

The Release SYCL build completed all 201 Ninja targets with Intel oneAPI
DPC++/C++ 2026.1.1, `STRATA_SYCL_PARITY=ON`, x86_64 CPU backend, and the pinned
local GGML checkout. GGML's SYCL backend was off; this built Strata's SYCL
parity path. `strata --help` returned 0; the binary hash is in
[`tests/sycl-binary-sha256.txt`](tests/sycl-binary-sha256.txt), and `ldd`
resolved `libsycl.so.9` from the retained toolchain.

CTest reported “No tests were found” for this build tree. The built
`conversation_snapshot_test` executable was therefore run directly; it passed
3,901 checks on maestro1's Intel OpenCL CPU device (Celeron N3450). The device
inventory shows no SYCL accelerator device. This is CPU-side SYCL runtime
evidence only; neither this test nor either backend build executed HIP kernels
on an AMD GPU or SYCL kernels on an accelerator.

The compiler emitted GCC-install-directory preference warnings and the SYCL
sources emitted unused-DPCT-helper warnings. Both full builds completed with
zero errors. These x86 results add build portability evidence; Orin performance
claims remain based only on native Orin runs.

## Reproduction

Use the tracked source commit and pinned dependency checkout from the metadata.
Set these paths to the isolated snapshot and existing toolchains on maestro1:

```sh
validation=/mnt/sda2/home/calvin/workspace/strata-validation
snapshot=$validation/phase8-current-source-d0baa266
rocm=$validation/toolchains/rocm/lib/python3.10/site-packages
ggml=$validation/dependencies/llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d
```

Configure and build the HIP variant in a clean build directory:

```sh
cmake -S "$snapshot" -B "$snapshot/build-hip" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_HIP_COMPILER="$rocm/_rocm_sdk_devel/llvm/bin/clang++" \
  -DCMAKE_HIP_COMPILER_ROCM_ROOT="$rocm/_rocm_sdk_devel" \
  -DCMAKE_HIP_ARCHITECTURES=gfx1100 \
  -DCMAKE_PREFIX_PATH="$rocm/_rocm_sdk_devel;$rocm/_rocm_sdk_libraries_gfx110X_dgpu" \
  -DCMAKE_HIP_FLAGS="--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/11 --rocm-path=$rocm/_rocm_sdk_devel --rocm-device-lib-path=$rocm/_rocm_sdk_devel/lib/llvm/amdgcn/bitcode" \
  -DHIP_PLATFORM=amd -DSTRATA_ENABLE_HIP=ON -DSTRATA_ENABLE_SYCL=OFF \
  -DSTRATA_BUILD_TESTS=ON -DSTRATA_PREFILL_MMQ=ON \
  -DSTRATA_GGML_DIR="$ggml" -DGGML_CUDA=OFF
cmake --build "$snapshot/build-hip" --parallel 1
```

For SYCL, source the oneAPI TBB, UMF, TCM, compiler, MKL and DPL environment
scripts, then configure and build:

```sh
oneapi=$validation/toolchains/intel-root/opt/intel/oneapi
source "$oneapi/tbb/2023.1/env/vars.sh"
source "$oneapi/umf/1.1/env/vars.sh"
source "$oneapi/tcm/1.5/env/vars.sh"
source "$oneapi/compiler/2026.1/env/vars.sh"
source "$oneapi/mkl/2026.1/env/vars.sh"
source "$oneapi/dpl/2022.13/env/vars.sh"
cmake -S "$snapshot/sycl" -B "$snapshot/build-sycl" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx \
  -DCMAKE_C_FLAGS=--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/11 \
  -DCMAKE_CXX_FLAGS=--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/11 \
  -DSTRATA_SYCL_PARITY=ON -DSTRATA_GGML_DIR="$ggml"
cmake --build "$snapshot/build-sycl" --parallel 1
```

The HIP smoke command was:

```sh
ctest --test-dir "$snapshot/build-hip" --output-on-failure \
  -R '^(shared_memory_budget_test|q8_oracle_contract_test|q2_portable_reference_test|expert_multi_test)$'
"$snapshot/build-hip/strata" --help
```

For SYCL, the selected CTest command was:

```sh
ctest --test-dir "$snapshot/build-sycl" --output-on-failure \
  -R '^(shared_memory_budget_test|q8_oracle_contract_test|q2_portable_reference_test|expert_multi_test)$'
```

CTest found no registered tests. The direct CPU-side test command was:

```sh
"$snapshot/build-sycl/conversation_snapshot_test"
```

The exact compiler paths, options, test commands and hashes are captured in
the accompanying metadata and test logs. This record does not imply a HIP GPU
or SYCL accelerator was available on maestro1.

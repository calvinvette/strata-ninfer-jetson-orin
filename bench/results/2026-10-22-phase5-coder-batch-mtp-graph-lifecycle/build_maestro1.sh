#!/usr/bin/env bash
set -euo pipefail
validation="$HOME/workspace/strata-validation"
work="$validation/integration/strata-ninfer-phase8-20261017"
logs="$work/logs/phase5-boundary-final-20261022"
mkdir -p "$logs"
(cd "$work/source" && sha256sum include/strata/core/verify.hpp src/core/verify.cpp src/program/generate.cpp) \
    > "$logs/source-manifest.sha256"
scratch=/mnt/sda2/tmp/strata-integration-20261022
mkdir -p "$scratch"
export TMPDIR="$scratch"
export PATH="$validation/toolchains/build-tools/bin:$PATH"
rocm_root=$("$validation/toolchains/rocm/bin/rocm-sdk" path --root)
rocm_libraries="$validation/toolchains/rocm/lib/python3.10/site-packages/_rocm_sdk_libraries_gfx110X_dgpu"
export HIP_PLATFORM=amd HIP_COMPILER=clang HIP_RUNTIME=rocclr
export ROCM_PATH="$rocm_root" HIP_PATH="$rocm_root"
export PATH="$rocm_root/bin:$rocm_root/llvm/bin:$PATH"
export LD_LIBRARY_PATH="$rocm_root/lib:$rocm_libraries/lib:${LD_LIBRARY_PATH:-}"
cmake --build "$work/build-hip" --parallel 1 > "$logs/hip-build.txt" 2>&1
sha256sum "$work/build-hip/strata" > "$logs/hip-binary.sha256"
"$work/build-hip/strata" --help > "$logs/hip-help.txt" 2>&1
set +u
oneapi="$validation/toolchains/intel-root/opt/intel/oneapi"
source "$oneapi/tbb/2023.1/env/vars.sh"
source "$oneapi/umf/1.1/env/vars.sh"
source "$oneapi/tcm/1.5/env/vars.sh"
source "$oneapi/compiler/2026.1/env/vars.sh"
source "$oneapi/mkl/2026.1/env/vars.sh"
source "$oneapi/dpl/2022.13/env/vars.sh"
set -u
cmake --build "$work/build-sycl" --parallel 1 > "$logs/sycl-build.txt" 2>&1
sha256sum "$work/build-sycl/strata" > "$logs/sycl-binary.sha256"
"$work/build-sycl/strata" --help > "$logs/sycl-help.txt" 2>&1
printf 'HIP/SYCL compile/link and CLI help passed; accelerator runtime not tested.\n' > "$logs/result.txt"

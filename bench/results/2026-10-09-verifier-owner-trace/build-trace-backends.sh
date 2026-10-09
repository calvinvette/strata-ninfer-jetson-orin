#!/usr/bin/env bash
set -euo pipefail
trace_root="$HOME/workspace/strata-integration-validation"
validation_tools="$HOME/workspace/strata-validation"
export TMPDIR="$validation_tools/tmp"
export PATH="$validation_tools/toolchains/build-tools/bin:$PATH"
rocm_root=$("$validation_tools/toolchains/rocm/bin/rocm-sdk" path --root)
rocm_libraries="$validation_tools/toolchains/rocm/lib/python3.10/site-packages/_rocm_sdk_libraries_gfx110X_dgpu"
export HIP_PLATFORM=amd HIP_COMPILER=clang HIP_RUNTIME=rocclr
export ROCM_PATH="$rocm_root" HIP_PATH="$rocm_root"
export PATH="$rocm_root/bin:$rocm_root/llvm/bin:$PATH"
export LD_LIBRARY_PATH="$rocm_root/lib:$rocm_libraries/lib:${LD_LIBRARY_PATH:-}"
cmake -S "$trace_root/source" -B "$trace_root/build-hip" -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_HIP=ON -DSTRATA_ENABLE_CUDA=OFF \
 -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_CONVERSATION_TESTS=ON \
 -DSTRATA_PREFILL_MMQ=ON -DCMAKE_HIP_ARCHITECTURES=gfx1100 \
 -DCMAKE_HIP_COMPILER="$rocm_root/llvm/bin/clang++" \
 -DCMAKE_HIP_COMPILER_ROCM_ROOT="$rocm_root" \
 -DCMAKE_PREFIX_PATH="$rocm_root;$rocm_libraries" \
 -DCMAKE_HIP_FLAGS="--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/11 --rocm-path=$rocm_root --rocm-device-lib-path=$rocm_root/lib/llvm/amdgcn/bitcode" \
 -DSTRATA_GGML_DIR="$validation_tools/dependencies/llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d" \
 > "$trace_root/logs/hip-configure.txt" 2>&1
cmake --build "$trace_root/build-hip" --parallel 1 > "$trace_root/logs/hip-build.txt" 2>&1
printf 'HIP build passed\n' > "$trace_root/logs/hip-result.txt"
# Vendor setup scripts access unset variables; enable nounset after sourcing.
set +u
oneapi_root="$validation_tools/toolchains/intel-root/opt/intel/oneapi"
source "$oneapi_root/tbb/2023.1/env/vars.sh"
source "$oneapi_root/umf/1.1/env/vars.sh"
source "$oneapi_root/tcm/1.5/env/vars.sh"
source "$oneapi_root/compiler/2026.1/env/vars.sh"
source "$oneapi_root/mkl/2026.1/env/vars.sh"
source "$oneapi_root/dpl/2022.13/env/vars.sh"
set -u
cmake -S "$trace_root/source/sycl" -B "$trace_root/build-sycl" -G Ninja \
 -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=icx -DCMAKE_CXX_COMPILER=icpx \
 -DCMAKE_C_FLAGS=--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/11 \
 -DCMAKE_CXX_FLAGS=--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/11 \
 -DSTRATA_SYCL_PARITY=OFF \
 -DSTRATA_GGML_DIR="$validation_tools/dependencies/llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d" \
 > "$trace_root/logs/sycl-configure.txt" 2>&1
cmake --build "$trace_root/build-sycl" --parallel 1 > "$trace_root/logs/sycl-build.txt" 2>&1
printf 'SYCL build passed\n' > "$trace_root/logs/sycl-result.txt"

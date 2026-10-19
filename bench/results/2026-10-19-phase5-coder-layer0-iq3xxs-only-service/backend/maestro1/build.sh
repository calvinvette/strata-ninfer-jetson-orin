#!/usr/bin/env bash
set -euo pipefail
trace_root=/dev/shm/phase5-q8-selector-maestro1
validation_tools="$HOME/workspace/strata-validation"
export TMPDIR="$trace_root/tmp"
mkdir -p "$TMPDIR" "$trace_root/logs"
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
cmake --build "$trace_root/build-hip" --parallel 2 > "$trace_root/logs/hip-build.txt" 2>&1
sha256sum "$trace_root/build-hip/strata" "$trace_root/build-hip/native_expert_parity" > "$trace_root/logs/hip-binaries.sha256"
set +e
"$trace_root/build-hip/strata" --help > "$trace_root/logs/hip-help.txt" 2>&1
echo $? > "$trace_root/logs/hip-help-exit.txt"
set -e

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
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER="$oneapi_root/compiler/2026.1/bin/icx" \
  -DCMAKE_CXX_COMPILER="$oneapi_root/compiler/2026.1/bin/icpx" \
  -DCMAKE_C_FLAGS:STRING=--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/11 \
  -DCMAKE_CXX_FLAGS:STRING=--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/11 \
  -DSTRATA_SYCL_PARITY=OFF \
  -DSTRATA_GGML_DIR="$validation_tools/dependencies/llama.cpp-3cf03257f219afbe7334045ff7c6a06ac68c627d" \
  > "$trace_root/logs/sycl-configure.txt" 2>&1
cmake --build "$trace_root/build-sycl" --parallel 2 > "$trace_root/logs/sycl-build.txt" 2>&1
sha256sum "$trace_root/build-sycl/strata" > "$trace_root/logs/sycl-binary.sha256"
set +e
"$trace_root/build-sycl/strata" --help > "$trace_root/logs/sycl-help.txt" 2>&1
echo $? > "$trace_root/logs/sycl-help-exit.txt"
set -e
scope_path=$(awk -F: '$1 == "0" {print $3}' /proc/self/cgroup)
cat "/sys/fs/cgroup${scope_path}/memory.events" > "$trace_root/logs/memory.events"
printf 'Exact-source HIP and SYCL compile/link completed. No accelerator execution was performed.\n' > "$trace_root/logs/result.txt"

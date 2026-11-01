# JetPack 7 (CUDA 13.2) validation on Jetson AGX Orin 64 GB — 2026-11-01

## Result

Before this change, `./setup.sh` stopped on JetPack 7 with "Jetson Orin needs the JetPack CUDA 12.6 toolkit":
JetPack 7 ships CUDA 13.x and no 12.x toolkit. With the change, setup selected
`/usr/local/cuda-13.2/bin/nvcc` on its own (CUDA 13.4 was also installed; the driver reports CUDA 13.2), compiled
the engine from a clean build folder with ccache disabled, prepared Q2_0 and IQ3_S packs, and wrote working
configurations. The engine links the CUDA 13.2 runtime and cuBLAS (`ldd` below).

| Check | Result |
| --- | --- |
| `tools/test_setup_jetson.py` | 21 of 21 pass, 6 of them new. On the previous `setup.py` the three JetPack 7 toolkit tests and the new message check fail; the JetPack 6.2 test passes on both. |
| All `tools/test_setup_*.py` on the Orin | 29 files, 439 tests (433 before). The same four files fail before and after the change ([before](setup-tests-before.txt), [after](setup-tests-after.txt)); see [Setup tests](#setup-tests). |
| CUDA functional CTest suite, serial | 124 registered, 122 passed, 2 failed for missing default input files ([output](ctest-output.txt)). 306 s. Minimum available RAM 46.3 GiB. Both passed when given their inputs (next rows). |
| `ple_parity` with real inputs | Passed: 0 failures, worst stage relative error 1.148e-07. |
| `pool_test` and `expert_parity` with a one-layer Q2_0 fixture | Both passed ([output](fixture-ctest-output.txt)). The fixture regenerated with `tools/pack_layer.py` has the same SHA-256 as the one in the [2026-10-22 regression report](../2026-10-22-phase5-current-source-regression/fixture-source-sha256.txt). |
| Q2_0 served answers | All 18 screening requests below returned 64 tokens of on-topic text, and profiles A and B begin the same way for the same prompt (text and hashes in the per-run JSON). Output quality was not scored. |

This shows that the CUDA 13.2 build compiles, passes the repository's functional tests and serves the real model
on this device. It is not a paired comparison with CUDA 12.6: JetPack 7 has no CUDA 12.6 toolkit, so no same-device
control exists. The speed numbers below are screening measurements as defined in
[the measurement protocol](../../../docs/integration/BENCHMARKS.md), not a confirmation.

## Hardware and software

- Board: NVIDIA Jetson AGX Orin Developer Kit, 64 GB (61.4 GiB visible), 12 Cortex-A78AE cores, MAXN power mode.
  No clock settings were changed; observed CPU 2.2016 GHz and GPU 1.3005 GHz during the CTest run. EMC clock readback
  needs root and was not recorded.
- Storage: WD_BLACK SN850X 1 TB NVMe.
- L4T R39.2.1 (JetPack 7), kernel 6.8.12-1021-tegra, Ubuntu 24.04.5 LTS, driver 595.78 (CUDA driver API 13.2).
- Toolkits installed: CUDA 13.2 (V13.2.86) and CUDA 13.4. GCC 13.3.0, CMake 3.28.3, Ninja 1.11.1, Python 3.12.3.
- Background processes during all runs: a resident PyTorch training worker (about 3 GB RSS, idle) and a
  llama-server serving a 0.5B model (about 0.8 GB RSS). 2 GiB of swap was already full before the runs.
- Source: `7178ce40` plus the `setup.py` and `tools/test_setup_jetson.py` changes in this branch (the files on the
  device matched the commit by SHA-256).

## Build identity

`./setup.sh --yes --setup --family qwen --model IQ3_S --gguf-dir <models> --context 262144 --vision no --no-start`
after deleting `build-cuda12/` and `engine-cuda12/`, with `CCACHE_DISABLE=1`. Setup printed
`[ok] JetPack CUDA toolkit: CUDA 13.2 (/usr/local/cuda-13.2/bin/nvcc)` and ran:

```text
cmake -G Ninja -S . -B build-cuda12 -DCMAKE_BUILD_TYPE=Release -DSTRATA_ENABLE_CUDA=ON -DSTRATA_BUILD_TESTS=OFF
  -DCMAKE_CUDA_ARCHITECTURES=87 -DCMAKE_CUDA_COMPILER=/usr/local/cuda-13.2/bin/nvcc
  -DCUDAToolkit_ROOT=/usr/local/cuda-13.2 -DSTRATA_GGML_DIR=third_party/llama.cpp -DSTRATA_EXPERIMENTAL_SM60=ON
cmake --build build-cuda12 --target strata -j 6
```

- `engine-cuda12/strata` SHA-256 `c8434642ded80bd63d0e2731903357e60629fbdaad4d3302bb1b110bfe1563e2`
  ([BUILD.json](BUILD.json)); compiler warnings only.
- `ldd`: `libcudart.so.13`, `libcublas.so.13` and `libcublasLt.so.13` from `/usr/local/cuda-13.2/lib64`.
- `-DSTRATA_EXPERIMENTAL_SM60=ON` is kept because it is the flag every earlier Orin measurement used. On sm_87 it
  adds Pascal/Volta kernels and admits older devices; OFF was not tested on Orin.

The CTest tree was configured separately with the same flags and `-DSTRATA_BUILD_TESTS=ON` in
`build/integration/jp7-ctest` (not committed).

## Setup tests

`tools/test_setup_*.py`, each run with the repository's `.venv` Python 3.12.3 on the Orin, before and after the
change on the same checkout:

| | Files | Tests | Files with failures |
| --- | ---: | ---: | --- |
| Before (`7178ce40`) | 29 | 433 | `test_setup_choices` (2 errors), `test_setup_engine_hash` (2), `test_setup_pins` (4), `test_setup_unsloth` (18 errors) |
| After | 29 | 439 | the same four, with the same counts |

The four files fail on an ARM64 host without this change. They exercise the x86 ready-made engine download and
fallback paths, which setup deliberately skips on ARM64 (`arm64_host()`), for example "No such file or directory:
'.../build/strata'" and "SystemExit not raised". On macOS (arm64, Python 3.14, a sparse checkout) the full set was
also identical before and after: 433 and 439 tests, the same seven files failing.

## CUDA functional suite

```sh
python3 tools/integration/run_control.py --output build/integration/jp7-ctest-run/supervisor \
  --timeout 5400 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/jp7-ctest --output-on-failure -j1
```

124 tests registered in this checkout (the 2026-10-24 report registered 135 with its fixtures configured; tests that
need absent fixture files are not registered here). 122 passed. The two failures could not open their default input
paths:

- `ple_parity`: `../../Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf`. Rerun with the real Q2_0 pack and
  shard 2 (`--pack <Strata-data>/packs/q2_0 --gguf <models>/...-Q2_0-00002-of-00002.gguf --selftest`): passed.
- `pool_test`: `pack/full/experts.bin`, the same failure as the
  [2026-10-24 CUDA 12.6 run](../2026-10-24-orin-cuda-functional-ctest/README.md). The one-layer S2 fixture was
  rebuilt with `tools/pack_layer.py` from the Q2_0 shard 1 (`build(1, ...)` with `SHARD1` pointed at the local
  file); `experts.bin` and `experts.json` match the published hashes ([fixture-sha256.txt](fixture-sha256.txt)).
  With `STRATA_TEST_EXPERTS_BIN` set to it, `pool_test` and `expert_parity` passed.

With their inputs supplied, all 124 registered tests passed. [ple_parity output](ple-parity-output.txt).

## Q2_0 on the CUDA 13.2 build (screening)

Model: ISTA-DASLab `Qwen3.8-Flash-Next-GSQ-RCO-GGUF` Q2_0 at revision `ed59f920`, shard SHA-256 `69820c02…` and
`316b46f3…`: the same bytes as the [2026-10-25 Q2_0 campaign](../2026-10-25-q2-current-candidate-performance/README.md).

Workload: the unchanged `make_request` of
[`run_cell.py`](../2026-10-25-flashnext-context-capacity-sweep/run_cell.py) (172/557/1,069 formatted prompt
tokens, thinking off, greedy, exactly 64 generated tokens, three rounds, no separate warmup, fresh prefill checked
by its cached-token assertion), driven by [`drive.py`](q2_0-screening/drive.py) against one server per profile:

- **A, setup's 64 GB default**: setup's configuration plus `--prompt-cache 0`
  ([config](q2_0-screening/config-a-installed.json)): all experts loaded into RAM (31.64 GiB), auto expert cache
  (5,956 slots, 7.67 GiB), whole-prompt prefill, MTP spec 4.
- **B, the author's qualified Q2_0 profile**: the
  [2026-10-25 template's](../2026-10-25-q2-current-candidate-performance/server-config.template.json) flags with
  this device's paths ([config](q2_0-screening/config-b-their-profile.json)): mapped experts, 3,000 requested slots,
  prefill 128, MTP drafts off. The template's own expert profile file is not in the repository; `data/expert-profile.bin`
  was used instead.

Medians of three requests in one server process (engine-reported prompt and decode rates, client-measured TTFT):

| Profile | 172 tokens PP / TG / TTFT | 557 tokens PP / TG / TTFT | 1,069 tokens PP / TG / TTFT | Min MemAvailable |
| --- | ---: | ---: | ---: | ---: |
| A, setup's 64 GB default | 139.3 / 25.8 / 1.4 s | 290.3 / 25.5 / 2.1 s | 399.0 / 26.5 / 2.8 s | 5 GiB |
| B, author's profile | 35.4 / 9.2 / 5.2 s | 64.4 / 13.0 / 8.9 s | 74.8 / 13.2 / 14.6 s | 40 GiB |

All 18 requests passed the script's checks. Ranges are in [summary.txt](q2_0-screening/summary.txt) and every row
is in `q2_0-screening/out-*/`. Each 172-token cell includes the first, cold request of its server (B's first decode
was 4.6 tok/s). Memory is `MemAvailable` sampled every 2 s and truncated to whole GiB; A ran at 5–7 GiB available
while serving, so on this shared machine it went below the 6 GiB floor that `run_control.py` enforces.

For orientation only: the 2026-10-25 Q2_0 sweep reported 30.9/11.8, 45.0/11.4 and 51.1/12.7 tok/s (PP/TG) for
profile B's settings on a 32 GB Orin with JetPack 6.2. That is a different device, memory size, JetPack, expert profile
file and day, not a paired control, so the difference is not attributed to CUDA 13.

## Not tested

- A CUDA 12.6 build on this device, and this change on a 32 GB Orin or on JetPack 6.2 hardware (JetPack 6.2 is
  covered by unit tests only).
- An engine built with a toolkit newer than the driver (CUDA 13.4 on a 13.2 driver); the code warns and proceeds.
- `-DSTRATA_EXPERIMENTAL_SM60=OFF` on Orin.
- HIP and SYCL builds. Only Jetson branches of `setup.py` changed.
- Confirmation-level runs (seven independent processes), energy, EMC clocks and output quality.

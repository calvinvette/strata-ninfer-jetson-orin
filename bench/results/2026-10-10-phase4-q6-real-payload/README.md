# Q6_K real-payload FP16 materialization — Orin — 2026-10-10

This CUDA-only diagnostic compares the existing `dequant_f16(14, ...)` path
with the CPU Q6_K artifact decoder and the independent nearest-half oracle on
four real rows from each Q6_K matrix shape seen in the current `pp512+tg64`
Nsight request profile. The test is opt-in and does not change runtime
dispatch. It reads model files from `~/models/`; no model data is copied into
the repository.

| GGUF tensor | Matrix rows × columns | Values checked |
| --- | ---: | ---: |
| `blk.1.attn_gate.weight` | 6144 × 2560 | 10,240 |
| `blk.2.ffn_up_shexp.weight` | 640 × 2560 | 10,240 |
| `blk.0.attn_qkv.weight` | 10240 × 2560 | 10,240 |
| `blk.3.attn_k.weight` | 512 × 2560 | 10,240 |
| `blk.31.attn_q.weight` | 12288 × 2560 | 10,240 |

All 51,200 FP16 outputs matched exactly, and the copied packed source bytes
were unchanged. The diagnostic uses the CPU artifact decoder to produce the
real-payload FP32 values, then independently rounds those values to FP16 with
the nearest-even oracle. The existing Q6_K synthetic codec contract separately
checks the packed-field equation and GPU FP16 implementation against retained
logical quant/subscale inputs. Together these results validate the profiled
materialization conversion over real payloads and shapes; they do not validate
GEMM products, model quality, a complete layer output, or a performance win.

The test binary was built Release for CUDA 12.6 / SM87. Its SHA256 is
`42be09d6bd46b375543dbb052b943b1819963457a7592599f7251f7b374de0ce`. The
supervisor completed in 2.15 seconds and sampled minimum physical
`MemAvailable` of 26,371,641,344 bytes (24.55 GiB), above the required six-GiB
floor. Raw command result, stdout/stderr, memory samples and tegrastats are
retained in `supervisor/`; no energy claim is made. The two input shard
identities are those recorded in the [candidate profile's artifact manifest](../2026-10-10-phase4-candidate-request-profile/identities.json):
`e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` and
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`. The
active dequantizer source SHA256 is
`cced4c4178dd710e25189e5d2cb56af933362a6d1ac62d8e93d640ac494ac0ab`; the test
source SHA256 is
`9bcb0e4d0a899c811c0c6996f6f976fec24e3e80d1ea05e60b5e5b4988b3f455`.

The existing 15-case synthetic independent Q6_K codec contract was also
rerun under the same six-GiB supervisor: CTest passed 1/1, including all
42,565,632 FP32/BF16/FP16 conversion values and guards. Its raw CTest and
supervisor output are retained in `codec-regression/`.

## Resource and safety-tool results

The actual linked SM87 diagnostic library was inspected with CUDA 12.6.68
`cuobjdump --dump-resource-usage`. The `dequant_kernel<(int)14,H16>` entry uses
22 registers per thread, zero stack, zero spills, zero static shared memory,
and zero local memory. Its launch uses 256 threads per block. These are static
compiler resource counts, not measured occupancy, achieved bandwidth or
critical-path contribution. The library SHA256 is
`3aae54ba664a49d6e5e933e1ebb9423c306ffa840e51d54ad6cb37490c88b916`.

Runtime profiling did not yield hardware counters: Nsight Compute 2025.2.0
reported insufficient privileges to launch an application for profiling; the
supervisor records exit status 0 for the profiler process, but its stdout is
only the warning and contains no profile. The raw attempt is retained in
`ncu/supervisor/`. The
Compute Sanitizer memcheck attempt ran all five numerical comparisons
successfully, then reported `GPU debugging features are disabled` and exited
with its requested error code 99. It is unsupported on this device/configuration,
not a clean memory-safety result. Its command result, stdout/stderr and
supervisor telemetry are retained in `compute-sanitizer/supervisor/`. Neither
tool result is counted as a pass.

Reproduce on the Orin with the pinned ggml source available at
`/tmp/strata-orin-build/_deps/strata_llamacpp-src`:

```sh
cmake -S tests/integration -B build/integration/operator-tests \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DSTRATA_GGML_DIR=/tmp/strata-orin-build/_deps/strata_llamacpp-src
cmake --build build/integration/operator-tests \
  --target q6_k_real_payload_contract --parallel 1
python3 tools/integration/run_control.py \
  --output bench/results/NEW-q6-real-payload/supervisor --timeout 240 -- \
  build/integration/operator-tests/q6_k_real_payload_contract \
  ~/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  ~/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf
```

Resource report for the linked test library:

```sh
/usr/local/cuda-12/bin/cuobjdump --dump-resource-usage \
  build/integration/operator-tests/libintegration_codec_kernels.a
```

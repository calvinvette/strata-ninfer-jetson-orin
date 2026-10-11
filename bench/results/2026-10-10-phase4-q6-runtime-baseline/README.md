# Full-shape Q6_K to FP16 runtime baseline — Orin — 2026-10-10

This is an isolated, unprofiled baseline for the existing CUDA `dequant_f16`
path on five real IQ1_M Q6_K dense matrices identified in the request trace.
The full packed matrix is copied to a device allocation before timing; each
matrix is warmed five times, then timed in seven seeded-randomized shape-order
blocks, with 20 launches per timed block. The median is over seven block
averages. The timed interval includes repeated CUDA launches and conversion,
but excludes GGUF loading, allocation and the initial host-to-device copy.

| Matrix rows × columns | Tensor | Input MiB | FP16 output MiB | Median per launch (ms) | Seven-block range (ms) | Nominal read+write GB/s |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 6144 × 2560 | `blk.1.attn_gate.weight` | 12.305 | 30.000 | 2.389398 | 2.382458–2.398365 | 18.565 |
| 640 × 2560 | `blk.2.ffn_up_shexp.weight` | 1.282 | 3.125 | 0.250606 | 0.250203–0.251194 | 18.438 |
| 10240 × 2560 | `blk.0.attn_qkv.weight` | 20.508 | 50.000 | 3.955130 | 3.939170–3.969424 | 18.693 |
| 512 × 2560 | `blk.3.attn_k.weight` | 1.025 | 2.500 | 0.197917 | 0.197528–0.198938 | 18.678 |
| 12288 × 2560 | `blk.31.attn_q.weight` | 24.609 | 60.000 | 4.759488 | 4.745070–4.820704 | 18.641 |

The last column is calculated from nominal Q6_K source bytes plus FP16 output
bytes divided by event time. It is not hardware-counter bandwidth; Nsight
Compute could not launch for profiling on this Orin due to missing profiling
privileges. Events are warmed repeated reads of the same device-resident tensor,
not streamed production misses. GPU/EMC clocks and energy were unavailable.
No optimization candidate or end-to-end benefit is established. The separate
[real-payload contract check](../2026-10-10-phase4-q6-real-payload/README.md)
provides the exact-output check for four real rows of each shape.

The run used CUDA 12.6.68 / SM87 Release code and a six-GiB supervisor. Minimum
physical `MemAvailable` was 30,085,120,000 bytes (28.02 GiB). The final raw-
sample benchmark binary SHA256 is
`fb16643765f5705b82831fe7ee339708a2cec3793f763e84f69678d5f84f250e`; input
shard identity is recorded in the [candidate request profile](../2026-10-10-phase4-candidate-request-profile/identities.json).
Raw block order/timings, stdout/stderr, supervisor result, memory samples and
tegrastats are retained in `supervisor-final/`. An earlier passing run before
raw block values were printed is retained in `supervisor/` and is excluded from
the table.

Reproduce:

```sh
cmake -S tests/integration -B build/integration/operator-tests \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DSTRATA_GGML_DIR=/tmp/strata-orin-build/_deps/strata_llamacpp-src
cmake --build build/integration/operator-tests \
  --target q6_k_real_payload_bench --parallel 1
python3 tools/integration/run_control.py \
  --output bench/results/NEW-q6-runtime-baseline/supervisor --timeout 300 -- \
  build/integration/operator-tests/q6_k_real_payload_bench \
  ~/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf
```

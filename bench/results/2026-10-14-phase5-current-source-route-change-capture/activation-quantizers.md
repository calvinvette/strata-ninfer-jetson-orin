# Captured activation quantizer comparison

This source-based diagnostic compares the CPU and CUDA activation formats on
the same seven captured layer-0 vectors (2,560 FP32 values each) used by the
route-flip sweep. `analyze_activation_quantizers.py` transcribes the finite
value contracts in `src/kernels/cpu/native_expert.cpp`, GGML's Q8_K reference
quantizer, `include/strata/kernels/q8_1_finite.hpp`, and the CUDA Q8_1 path in
`src/kernels/cuda/iq_kernels.cu`. The script uses only Python's standard
library and can be rerun from any directory.

| Captured row | CPU Q8_K relative L1 vs FP32 | CUDA Q8_1 relative L1 vs FP32 | Q8_K/Q8_1 mutual relative L1 | unequal reconstructed values |
|---|---:|---:|---:|---:|
| 0 | 1.29388% | 0.82420% | 1.24028% | 2434 / 2560 |
| 1 | 1.08659% | 0.76806% | 1.08055% | 2460 / 2560 |
| 2 | 1.16225% | 0.77857% | 1.14816% | 2349 / 2560 |
| 3 | 1.12550% | 0.76861% | 1.12929% | 2461 / 2560 |
| 4 | 1.18858% | 0.77205% | 1.14683% | 2271 / 2560 |
| 5 | 1.16040% | 0.79701% | 1.14713% | 2461 / 2560 |
| 6 | 1.05899% | 0.75157% | 1.06049% | 2307 / 2560 |
| Median | 1.16040% | 0.77205% | 1.14683% | — |

The difference is present in the activation image before expert matrix
arithmetic. This gives a concrete mechanism consistent with the isolated
CPU/GPU expert-output differences in `README.md`. It does not establish how
much activation quantization contributes relative to packed-weight dot-product
arithmetic, nor does it prove that the quantizer difference causes the
short/long/short persistent-state drift. The measurements are reconstructed
vectors, not a device capture of Q8_1 bytes; Q8_1's stored half sum and the
format-specific dot implementation are outside this vector comparison. The
existing `native_expert_parity` run remains the actual CPU/GPU operator check.

Reproduce with:

```sh
python3 bench/results/2026-10-14-phase5-current-source-route-change-capture/analyze_activation_quantizers.py
```

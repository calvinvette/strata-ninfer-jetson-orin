# Decomposing CPU/GPU expert output differences — Orin — 2026-10-15

This follow-up isolates the activation-format part of the six layer-0
CPU-to-GPU expert route flips captured in the
[route-change experiment](../2026-10-14-phase5-current-source-route-change-capture/README.md).
For each captured FP32 input, the parity tool dequantized the exact IQ3_XXS
gate/up and IQ4_NL down weights with GGML's type decoder. A separate CBLAS
FP32 oracle then ran the expert with reconstructed CPU-path Q8_K/Q8_0
activations and GPU-path Q8_1/Q8_1 activations. Q8_K and Q8_1 are transcribed
in
`../2026-10-14-phase5-current-source-route-change-capture/analyze_activation_quantizers.py`;
Q8_0 is transcribed from GGML's `quantize_row_q8_0_ref` in
`analyze_oracles.py`.
No inference code or default behavior changed; weight dumps were removed after
analysis and can be regenerated from the model under `~/models/`.

For the first captured activation, the six actual CPU/GPU operator pairs and
the corresponding shared-weight quantization-only oracle were:

| Expert | Actual CPU/GPU relative L1 | Quantizer-only oracle relative L1 | Delta residual vs actual CPU/GPU difference |
| ---: | ---: | ---: | ---: |
| 32 | 1.47744% | 1.47744% | 0.00127% |
| 55 | 1.56539% | 1.56582% | 4.36760% |
| 70 | 1.63343% | 1.63343% | 0.00119% |
| 75 | 1.29302% | 1.29235% | 0.80940% |
| 119 | 1.61476% | 1.61883% | 5.17184% |
| 165 | 1.58266% | 1.58266% | 0.00119% |

The median actual CPU/GPU difference was 1.57402%; the median quantizer-only
difference was 1.57424%. The median residual vector was 0.40533% of the
measured CPU/GPU difference vector (range 0.00119–5.17184%). The actual CPU
output was within 0.000014% relative L1 of its Q8_K/Q8_0 oracle at worst; the
GPU output was within 0.083511% of its Q8_1/Q8_1 oracle at worst. Across all
seven captured activations and six experts, the 42 shared-weight oracle
pairs had median relative L1 1.50755% (range 0.63873–2.27971%).

This is strong evidence that the activation quantizer contracts explain
nearly all of the isolated layer-0 expert output gap on these inputs. It does
not prove that this arithmetic difference alone causes the service-level
short/long/short persistent-state drift, nor does it assess other layers,
experts or contexts. Phase 5 remains open; no numerical compatibility or
adaptive-swapping guarantee is inferred.

The experiment used Coder IQ1_M shard files from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. The exact shard hashes match the
earlier path report. The CUDA `native_expert_parity` build passed all 15
`native_expert_parity_*` CTests. Its opt-in dump mode passed on all six real
experts; `parity-output.txt` records the outputs. Minimum host availability
for the supervised dump was 27.02 GiB. A first wrapper attempt failed before
loading the model because its script root path was wrong; it is retained under
`supervisor/` and excluded. `supervisor-attempt2/` is the successful run.

The changed diagnostic source also compiled and linked as `native_expert_parity`
with HIP on maestro1 using Clang 22, GCC 11 headers, HIP gfx1100 and CMake
3.31.10, one build job. The binary SHA256 is in `hip-binary-sha256.txt`. This
is x86_64 compile/link evidence only; maestro1 has no qualified HIP device for
this test. The diagnostic target is not part of SYCL builds.

To reproduce, regenerate the temporary dequantized expert dumps, run the
oracle analysis, then the CTest suite:

```sh
python3 bench/results/2026-10-15-phase5-activation-error-decomposition/dump_experts.py
python3 bench/results/2026-10-15-phase5-activation-error-decomposition/analyze_oracles.py
ctest --test-dir build/integration/candidate -R '^native_expert_parity_' --output-on-failure
```

The analysis uses the exact captured activations and runs a CBLAS FP32
float-weight oracle; it does not reproduce packed-weight CPU/GPU dot
arithmetic. Raw activations, actual operator outputs, analysis JSON, source,
binary identities and supervised telemetry are retained. Dequantized model
weights are transient and are not committed.

# Layer-1 expert-3 owner change through the layer-2 GDN update

Date: 2026-10-31. Hardware: Jetson AGX Orin. This is a paired diagnostic and local recurrence counterfactual, not a performance or task-quality result.

## Setup

One fixed-owner and one adaptive strict-NInfer process used the same 65,536-token Q2_0 prompt and generated 32 tokens at temperature 0. Both used the 131,072 context, original expert profile, 3,000 cache slots, 6 GiB resident budget, 3 GiB workspace reserve, prefill 128, eight workers, MTP-2, PCIe staging off, and prompt cache off. The CUDA executable SHA-256 was `0b8eadf1f3894efe449d9b96082f7e83cd9aa2bf616f6161625b95f7001ccf37`. Both supervised runs passed and emitted the same 32 token IDs (SHA-256 `2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`). Minimum available physical RAM was 9.17 GiB fixed and 9.12 GiB adaptive; sampled cgroup OOM kills were zero. Peak sampled swap was 2.07 GiB. Clock sampling and energy measurement were not enabled. Capture instrumentation makes all timings unsuitable for performance use.

## Captured transition

At model layer 1, position 65,540, routes, route weights, and MoE input matched bit-for-bit. Expert 3 was GPU-owned in the fixed process and CPU-owned in the adaptive process. It was the only changed expert output row: 1,840/2,560 values differed (relative L2 `1.059e-7`, maximum absolute `1.49e-8`). The combined MoE output differed by relative L2 `4.345e-8`.

At the following model-layer-2 GDN update for the same token, the layer-2 pre-update recurrent state was bit-identical. Its input `x` differed at 786/2,560 values (relative L2 `5.57e-8`, maximum absolute `4.77e-7`). The projected `qkv`, recurrence input `h`, `z`, and `gdn_out` were bit-identical. The gate differed at 10/48 values and beta at 11/48, at relative L2 `1.20e-8` and `3.47e-8`. The layer-2 recurrent state first differed after this update; the convolution history remained bit-identical:

| Position | Token | Recurrent state difference | Relative L2 | Convolution history difference |
|---:|---:|---:|---:|---:|
| 65,536 | 32 | 0 / 786,432 | 0 | 0 / 30,720 |
| 65,537 | 6165 | 0 / 786,432 | 0 | 0 / 30,720 |
| 65,538 | 11036 | 0 / 786,432 | 0 | 0 / 30,720 |
| 65,539 | 1928 | 0 / 786,432 | 0 | 0 / 30,720 |
| 65,540 | 1472 | 97,439 / 786,432 | 1.65e-08 | 0 / 30,720 |
| 65,541 | 264 | 76,303 / 786,432 | 1.69e-08 | 0 / 30,720 |
| 65,542 | 6150 | 71,974 / 786,432 | 1.76e-08 | 0 / 30,720 |
| 65,543 | 11 | 68,072 / 786,432 | 1.76e-08 | 0 / 30,720 |

At positions 65,541–65,543, the captured GDN input and gate/beta values matched again, but the small recurrent difference persisted. The separate route trace found no other owner-kind change in model layers 0–2 across positions 65,536–65,542.

## Independent recurrence replay and counterfactual

The existing independent FP64 gated-delta oracle was replayed from each prior captured device state. Across positions 65,537–65,543 it reproduced the captured raw recurrence output within `7.93e-8` relative L2 (fixed) and `7.99e-8` (adaptive); replayed recurrent state differed from device state by at most `5.06e-8` relative L2. This checks the recurrence math and captured values independently of the CUDA kernel.

At position 65,540, a same-prestate counterfactual held `h` fixed (it is bit-identical between arms) and crossed the captured gate/beta vectors. Relative to the all-fixed FP64 recurrence, the all-adaptive gate/beta pair changed recurrent state by `1.244e-8` relative L2. Changing only gate produced `7.760e-9`; changing only beta produced `9.792e-9`. Both fields contribute; these effects are nonlinear and should not be added. The observed fixed/adaptive device recurrent-state difference was `1.652e-8` relative L2. The counterfactual is a recurrence replay over captured values, not a live forced-owner intervention.

## Interpretation and limits

This verifies a local sequence at one token: layer-1 expert 3 changes owner and output; layer-2 `x` changes slightly; layer-2 gate/beta change while `h` remains exact; and the recurrent update creates the first layer-2 recurrent-state difference. It supports gate/beta differences as the local cause of that update's state delta. The cross-layer captures align the upstream change with the owner switch, but no runtime intervention forced expert 3 to the other owner and replayed the complete model. This does not prove the owner switch is the sole source of later persistent-state divergence, generalize beyond this pair, or qualify model quality. No speed claim follows.

See the [machine-readable capture comparison](layer1-expert3-layer2-gdn-counterfactual-65540.json), [cross-layer owner scan](layer0-2-owner-window-65536-65542.md), and [independent recurrence oracle](../../../tools/integration/gdn_trace_oracle.py). Raw capture binaries and telemetry remain in `/tmp/e6-owner3-causal-{fixed,adaptive}*` and are not committed.

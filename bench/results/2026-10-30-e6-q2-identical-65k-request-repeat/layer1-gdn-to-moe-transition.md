# Layer-1 GDN and MoE transition at the final prompt token

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is an instrumented
same-process diagnostic for request repeatability, not a performance result.

## Setup

One strict-NInfer process handled the identical 65,536-token prompt twice,
with temperature 0, a 32-token generation limit, and 131,072-token context.
Prompt cache and PCIe staging were disabled. At model layer 1 and prompt
position 65,535, the run captured GDN intermediates, raw GDN output, and
pre/post recurrent state. Both records used token 271.

## Findings

All captured GDN intermediates and its MoE input matched bit-for-bit across
the two requests. The first difference in the captured layer-1 sequence was
the combined MoE output (`ffn_y` in this diagnostic's field naming):

| Field | Different values | Maximum absolute difference | Relative L2 |
| --- | ---: | ---: | ---: |
| GDN input `x` | 0 / 2,560 | 0 | 0 |
| `qkv` | 0 / 10,240 | 0 | 0 |
| `h` | 0 / 10,240 | 0 | 0 |
| `gate` | 0 / 48 | 0 | 0 |
| `beta` | 0 / 48 | 0 | 0 |
| `z` | 0 / 6,144 | 0 | 0 |
| `y` | 0 / 6,144 | 0 | 0 |
| GDN output | 0 / 2,560 | 0 | 0 |
| MoE input (`ffn_x`) | 0 / 2,560 | 0 | 0 |
| Combined MoE output (`ffn_y`) | 1,658 / 2,560 | 1.72993e-06 | 5.56115e-05 |

The model-layer-1 recurrent matrix and convolution history were exactly equal
both before and after this verifier window. The raw state comparison covered
786,432 recurrent-matrix and 30,720 convolution-history floats on each side.
The matching MoE input and differing combined output agree with the separate
[layer-1 boundary capture](layer1-boundary-transition.md), where the residual
and hyperconnection fields matched but the layer's output vector differed.

## Interpretation and next step

For this request and execution history, the first changed captured value is
downstream of layer-1 GDN: the MoE input is bit-identical and the combined MoE
output is not. The capture does not say whether routing, selected expert
partial outputs, weighted merging, or a numerical execution detail first
causes the output delta. Next capture model layer 1's full MoE bundle (routes,
weights, input, per-expert parts and combined output) for both requests. The
capture copies and synchronizes device data and may perturb scheduling. These
diagnostics make no speed or general determinism claim.

The paired 65K run passed. Supervised telemetry recorded 8.54 GiB minimum
available memory, 2.12 GiB peak swap use, and no cgroup OOM kills. Raw files
remain in `/tmp/e6-65k-ninfer-gdn-layer1-capture/`.

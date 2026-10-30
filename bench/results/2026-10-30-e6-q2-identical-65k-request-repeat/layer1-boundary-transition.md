# Model-layer-1 boundary at the final prompt token

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is an instrumented,
same-process repeatability diagnostic, not a performance or quality result.

## Setup

One strict-NInfer process handled the same 65,536-token prompt twice, at
temperature 0, with a 32-token generation limit and 131,072-token context.
Prompt cache and PCIe staging were disabled. The opt-in residual/hyperconnection
capture recorded model layer 1 at position 65,535 for both requests. The
current CUDA executable was used; the capture synchronized device data and can
perturb scheduling.

## Result

Both requests passed and captured the same boundary record identity (model
layer 1, position 65,535, token 271). The main residual stream and
hyperconnection term at the layer output were bit-identical, while the layer's
MoE/output vector differed slightly:

| Field | Different values | Maximum absolute difference | Relative L2 |
| --- | ---: | ---: | ---: |
| Layer output residual stream (`rt`) | 0 / 10,240 | 0 | 0 |
| Layer output MoE vector | 1,658 / 2,560 | 1.72993e-06 | 5.56115e-05 |
| Layer output hyperconnection term (`inj2`) | 0 / 4 | 0 | 0 |
| Next-layer residual stream | 0 / 10,240 | 0 | 0 |
| Next-layer MoE vector | 1,658 / 2,560 | 1.72993e-06 | 5.56115e-05 |
| Next-layer hyperconnection term | 0 / 4 | 0 | 0 |
| Next-layer post-read residual state | 6,169 / 10,240 | 2.65311e-07 | 4.50636e-06 |
| Next-layer normalized input (`xn`) | 8,816 / 10,240 | 1.99080e-04 | 2.59691e-05 |

The preceding [layer-2 raw capture](gdn-layer2-raw-transition.md) found an
already-different layer-2 input activation (2,554/2,560 values, relative L2
`3.10649e-05`) while layer-2 entering recurrent state was exact. This layer-1
boundary therefore narrows the earlier activation change to the model-layer-1
output path: the residual and hyperconnection fields match, but the MoE/output
field does not. It does not yet identify the internal layer-1 operation that
first differs.

The run completed both requests successfully. Supervised telemetry recorded
8.36 GiB minimum available memory, 4.38 GiB peak swap use, and no cgroup OOM
kills. Raw capture, logs, results and telemetry remain in
`/tmp/e6-65k-ninfer-layer1-boundary/`.

## Interpretation and next step

The first observed changed layer-boundary field is model layer 1's MoE/output
vector, at a very small magnitude. The next diagnostic is to capture the
layer-1 GDN projection, recurrence and FFN intermediates together with its
pre/post state. This should distinguish a small branch-input/projection delta
from a later output-combination delta. The evidence is specific to this model,
prompt, build and runtime history; it is not a general determinism claim.

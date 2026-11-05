# First layer-0 numerical divergence in Coder service replay

Date: 2026-11-05. Jetson Orin AGX, Coder IQ1_M, held-out `is_even(n)` prompt,
position 41 (token 271). This is a targeted E5 numerical diagnosis, not a
performance or general model-quality result.

## Paired service capture

Under the matched static profile, layer-0 GDN inputs and stages through
`ffn_x` were bit-identical between Strata and strict NInfer. MoE route IDs,
weights and inputs were also exact. The dispatch owner trace assigned five of
the ten experts to GPU and five to CPU. All five CPU expert outputs were
bit-identical across backends. Every GPU-owned expert row differed slightly:
relative L2 ranged from `8.39e-8` to `8.54e-8`, with maximum element deltas
from `1.12e-8` to `1.49e-8`. The combined MoE output differed in 939/2,560
values, at relative L2 `3.50e-8` and maximum absolute delta `7.45e-9`.

The independent same-input CUDA oracle reproduces each of the five GPU-row
deltas. Its gate and up projections match exactly and its intermediate hidden
Q8_1 bytes match in all 720 bytes. The remaining difference is therefore in
the IQ4_NL down projection. Source inspection shows different accumulation
layouts: NInfer sums per-block dot products with a full-warp reduction, while
the native CUDA path splits work across eight-lane subwarps and uses a
different reduction tree. This is consistent with the observed few-ULP output
change; it is not yet a fix or an accepted state-drift tolerance.

At the next layer, the captured input delta is only `3.80e-7` relative L2.
For routed expert 198, one of 80 Q8_1 input blocks crosses an FP16 scale
rounding boundary while all integer codes remain equal. The CUDA quantizer
matches the independent oracle for both activations. The same-input expert
kernel oracle is exact for that layer-1 row. Together, the captures identify a
plausible amplification chain for this prompt position: a very small NInfer
layer-0 down-projection rounding delta propagates into the next-layer
activation, where Q8_1 scale rounding changes, then the quantized MoE output
diverges more substantially. This does not prove that the same chain explains
all requests or all later recurrent-state differences.

Structured per-expert data and the layer-0 stage comparison are in
[`summary.json`](summary.json). Raw captures remain in `/tmp` and are not
committed. The supervised service pair retained at least 20.97 GiB available
physical RAM; the separate ten-row oracle retained at least 24.36 GiB. Both
were above the six-GiB floor, and the pre-existing cgroup OOM-kill counter
stayed at one. Clocks were observed and dynamic; EMC readback was denied and
energy was not measured. Instrumented timings are excluded.

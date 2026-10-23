# Captured SwiGLU hidden-scale boundaries — Orin — 2026-10-20

This analysis compares three same-input CPU/GPU expert captures retained with
the layer-16, layer-31 and layer-39 reports. Each pair has matching Q8_1
integer codes and sum scales in the affected blocks; only the FP16 `d` scale
changes. The analyzer records the CPU prequantization `amax/127` relative to
the midpoint between the captured CPU and GPU half scales. It does not infer
same-input identity itself; each pair's source report establishes that link.

| Capture | Changed blocks | CPU scale | GPU scale | CPU scale vs half midpoint |
|---|---:|---|---|---:|
| Layer 16, expert 118, direct-division trial | 10, 30, 50 | `de16` | `dd16` | exactly at midpoint |
| Layer 31, expert 22, direct-division trial | 12, 32, 52 | `781a` | `791a` | exactly at midpoint |
| Layer 39, expert 90, default Q8_1 stage | 1, 21, 41 | `3b23` | `3a23` | 2 float32 ULP above midpoint |

For layer 16, the CPU maximum is `0.212862491608` and its float32 `amax/127`
is exactly the half-scale midpoint `0.00167608261108`. The source-faithful
CUDA replay's maximum is one float32 representable value lower
(`0.212862461805`), putting its scale below the midpoint. The round-to-nearest,
ties-to-even conversion therefore selects adjacent half scales. At layer 31,
the captured direct-division CPU scale also lands exactly at a midpoint, but
the GPU stored scale is the upper neighbor; the direction is reversed. The
layer-39 CPU scale is above its midpoint, so a tie-only adjustment would not
change it.

This rejects a global “round exact scale ties down” correction: it would fix
the layer-16 captured blocks and make the layer-31 direct-division capture
worse, while it would not address the layer-39 mismatch. The layer-31
reciprocal-expression variant is separately bit-exact for that capture, and
the layer-39 direct-division variant is separately bit-exact there; these
cross-effects are why neither algebraic expression is promoted globally.
The observed seam is sensitive to the CPU/GPU SwiGLU float value before
quantization, and no general correction or long-chain drift contract follows
from these three operator samples.

The retained [JSON output](hidden-q8-scale-tie-analysis.json) was generated
with [`analyze_hidden_q8_scale_ties.py`](analyze_hidden_q8_scale_ties.py) from
these explicit capture paths. The analyzer reports scale bytes, sums, code
differences and midpoint distance. It is a diagnostic helper, not a validator
that two arbitrary files came from the same activation.

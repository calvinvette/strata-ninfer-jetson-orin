# Corrected Q8_1 grouped SwiGLU parity replay

This repeats the layer-3 / expert-94 standalone replay after changing the
NInfer grouped SwiGLU expression to match Strata's precise division path. The
standalone Q2_0 scalar D3/D4 oracle remains passing (relative L2
`2.05e-7`, max absolute `1.49e-8`). Grouped gate and up projections are exact,
all 720 SwiGLU Q8_1 bytes now match, and the grouped resident route is bitwise
identical to Strata (relative L1 0; harness pass).

At this captured one-entry case the device-time ratio was 0.994×. Full grouped
64-token operator timing remained slower at 1.098×, and 128-token timing at
1.123×. The correction fixes the observed parity issue; it does not make the
grouped operator faster at larger widths. The complete parity output and
supervised resource record are retained under `supervisor/`.

# Layer-2 upstream-change capture — Orin — 2026-10-19

This fixed-residency pair captured layer-2 device inputs, expert IDs, router
weights and outputs for the same Coder IQ1_M prompt and the same default-CPU
versus Q8_1-mirror arms used in the
[layer-1 weighted reconstruction](../2026-10-19-phase5-coder-layer1-weighted-output-pair/README.md).
Each service generated the same 16 completion IDs and used a 28-GiB supervised
scope.

At position 511/token 271, all ten expert IDs matched, but the layer-2 device
input differed in all 2,560 values (maximum absolute delta `0.0072663`) and all
ten float32 router weights differed (maximum absolute delta `0.00014855`). The
combined layer-2 output differed in all 2,560 values (maximum absolute delta
`0.00062274`). Therefore the same-input weighted analyzer rejected this cell;
it cannot isolate layer-2 arithmetic. This is the expected downstream
signature after the independently reconstructed layer-1 output change.

The randomized order was `cpu_default`, then `cpu_mirror`. Minimum
host/admission availability was 14.37/14.37 GiB for default CPU and
14.42/14.42 GiB for the mirror. Both supervisors passed the six-GiB floor.
The machine used dynamic clocks; EMC readback was denied and energy was not
attributed. The raw route/activation/output captures and supervisor telemetry
are retained here. The standalone summary is
`analysis-upstream-difference.json`.

The attempted weighted reconstruction is intentionally retained as a failed
cell: `analyze_layer_weighted_delta.py` exited with
`device top-k IDs or router weights differ across arms` after checking that
the required equality conditions did not hold. The separate mismatch analyzer
reproduces the reported comparison with:

```sh
python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_layer2_route_mismatch.py
```

No weighted arithmetic, persistent-state or answer-quality conclusion is drawn
from this layer-2 pair.

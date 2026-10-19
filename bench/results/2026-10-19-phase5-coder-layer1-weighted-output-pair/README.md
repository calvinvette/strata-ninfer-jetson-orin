# Layer-1 weighted CPU-output delta reconstruction — Orin — 2026-10-19

This fixed-residency pair tests the earliest MoE layer implicated by the
Coder IQ1_M accepted-prefix divergence. It compares the production default CPU
expert arithmetic with the opt-in Q8_1 CPU mirror. Each fresh service used the
same 512-token incident prompt, FP16 KV, MTP2, fixed expert residency, no prompt
cache and 16 generated tokens. The services were run in randomized order with
28-GiB scopes and dynamic clocks observed.

At position 511/token 271, the layer-1 device input, top-10 expert IDs, float32
router weights and owner vector were bitwise identical between arms. Seven
experts were CPU-owned in both. Every CPU expert output differed in all 2,560
values; per-expert relative L1 ranged from 0.804% to 1.757%. Weighting these
seven CPU-output deltas reconstructs the combined device `ffn_y` delta across
all 2,560 values: maximum absolute residual `1.233e-8`, relative-L1 residual
`1.952e-5`. This directly attributes the first combined layer-1 output change
to the CPU arithmetic difference for this row, within float32 combination
rounding.

A separate capture on the same prompt compared the layer-2 verifier inputs.
Its position-511 `ffn_x` already differed in all 2,560 values, and all ten
router weights differed (maximum absolute delta `1.4855e-4`), while expert IDs
and completion IDs remained equal. The layer-2 weighted analyzer correctly
rejected that pair because its input/weight equality preconditions failed.
This confirms that the change is carried downstream from layer 1; it does not
attribute every later recurrent-state difference or establish answer-quality
impact.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned at
revision `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. The tested service
binary SHA256 is
`6de7699cb94c2efb5a7634dcddfdfdf4625cd91511340f519d225dc1e861a3f3`, built
from repository commit `ebef974c83b0e7bb08645abeea1166120aed7f95`. The exact
prompt token digest is
`e0bd698f8c50353ac64ce10b5ce3c6c8629e52839d7c3df9a90aec1cc7a19f91`.
Model files remained under `~/models/strata-orin-validation/`.

Both arms passed supervision with zero observed cgroup high/max/OOM/OOM-kill
events. Minimum host/admission availability was 14.41/14.41 GiB for default
CPU and 14.43/14.43 GiB for the Q8_1 mirror. EMC readback was denied and energy
was not attributed. These results support a numerical explanation for the
first layer output change in this request. They do not prove a full downstream
state cause, qualify Q8_1 as a serving default, or resolve Phase 5.

Reproduce the layer-1 pair from the repository root on Orin:

```sh
OUTROOT=bench/results/2026-10-19-phase5-coder-layer1-weighted-output-pair \
LAYER=1 bash bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_layer_weighted_pair.sh
```

The device-side inputs, route IDs/weights, CPU outputs, combined outputs,
request identities and supervisor telemetry are retained per arm. The
weighted reconstruction is in `analysis-weighted-delta.json`; the exact
same-input analyzer is
[`analyze_layer_weighted_delta.py`](../2026-10-18-phase5-coder-layer1-route-isolation/analyze_layer_weighted_delta.py).
The failed layer-2 same-input precondition and its measured differences are
retained in
[`2026-10-19-phase5-coder-layer2-weighted-output-pair`](../2026-10-19-phase5-coder-layer2-weighted-output-pair/README.md).

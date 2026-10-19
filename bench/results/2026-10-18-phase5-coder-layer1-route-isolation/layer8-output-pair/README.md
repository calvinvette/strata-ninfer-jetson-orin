# Layer-8 CPU expert arithmetic and device output — Orin — 2026-10-19

This two-arm supervised capture compares the default CPU route against the
opt-in Q8_1 CPU mirror while recording layer-8 device inputs, route IDs/owners,
CPU expert output rows and the combined device output. It uses the same pinned
Coder IQ1_M model, prompt and 16-token completion as the parent all-layer
campaign. Arm order was randomized (`cpu_mirror`, then `gpu_layer1`; the latter
is the default CPU-arithmetic control with the GPU-placement profile used to
provide the comparison captured in this campaign). Both runs used separate
28-GiB cgroup scopes and dynamic clocks.

At absolute position 511/token 271, the device `ffn_x` input, route IDs, owners
and the seven CPU-owned experts (19, 139, 221, 215, 192, 196, 167) match
exactly. Each of the seven CPU output vectors differs in all 2,560 values
between default and Q8_1 arithmetic (median relative L1 1.412%, range
1.189%–1.505%). The combined device `ffn_y` differs in all 2,560 values
(maximum absolute difference 0.0001266, relative L1 0.334%). This is a
same-input, same-route numerical comparison at the layer immediately before
the first layer-9 GDN divergence found in the paired trace; it does not by
itself attribute all downstream state or token changes to these rows.

A separate independent `native_expert_parity` oracle was run on the captured
position-511 activation and all seven native IQ2_S/Q2_0 experts. For each
expert, service output matched the corresponding independent parity-tool CPU
output bitwise in each arithmetic mode. Q8_1 CPU output matched CUDA bitwise
for all seven. Relative L1 against the float dequantized reference had a
median of 1.181% (range 1.099%–1.352%) for default CPU and 0.953% (range
0.908%–1.056%) for Q8_1. This checks one operator input, not complete expert
weighted-sum reconstruction or model quality. See `oracle/analysis-layer8.json`
and the retained per-expert stdout logs.

Both service captures passed: minimum host/admission availability was
14.40/14.40 GiB and 14.42/14.42 GiB, with zero observed cgroup high, max, OOM,
and OOM-kill events. The oracle passed in a separate 28-GiB scope with minimum
host availability 24.33 GiB and no cgroup memory events. No timing or energy
comparison is claimed. Recreate the service capture with
`../run_layer8_output_pair.sh` and rerun its analyses with:

```sh
python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_layer8_output_pair.py
python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_layer8_expert_oracle.py
```

The oracle requires the local model under
`~/models/strata-orin-validation/Coder-GGUF/IQ1_M/` and the built
`build/integration/candidate/native_expert_parity` tool. Failed and corrected
harness attempts are retained under `oracle/`. Phase 5 remains open.

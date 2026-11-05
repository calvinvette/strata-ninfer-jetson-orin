# Coder retrieval per-layer route and owner capture

This instrumented diagnostic used the same 2,048-token active-ticket retrieval
prompt, 4,096-token context, Coder IQ1_M artifact, and static 6 GiB PCIe
complement as the [timing screen](../README.md). Adaptive swaps were disabled.
It captured one request per backend with the opt-in MoE trace at every model
layer. Timing from these instrumented requests is excluded.

Both arms returned the exact six-token answer `73192` with identical token IDs.
The trace captured 288 layer/position rows across 48 layers and positions
2,047–2,052 (2,880 routed entries) in each arm. Owner totals matched exactly:
86 resident-GPU entries, 792 PCIe entries and 2,002 CPU/file entries. For every
expert selected by both arms at the same layer and position, its owner class
matched. The static profile therefore held ownership policy fixed at the
per-expert level.

The routed expert *sets* did not remain identical. They differed at 72 of 288
aligned layer/position rows; ordered top-10 IDs differed at 179 rows. For the
experts selected by both backends at a row, owner class was identical at every
row. Aggregate owner
counts being equal does not mean equal experts or equal work were executed.
This is an observed route-selection divergence under a matched prompt and
profile, despite identical output tokens. It limits causal interpretation of
the natural-generation timing screens. The capture does not by itself identify
which backend operation caused each route change or establish a quality error.

The tracked [`result.json`](result.json) contains route/owner counts and trace
hashes. Raw JSONL traces contain captured CPU activations and remain local to
the Orin workspace; they are not committed.

Reproduce from the project root on the Orin host:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/owner-capture-all-supervisor \
  --sample-clocks --timeout 2400 -- \
  python3 bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/capture_route_owners.py \
  bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/owner-capture-all
```

Minimum available/admission memory was 15.03 GiB, above the six-GiB floor;
the existing OOM-kill count remained one. Clocks were sampled read-only and
dynamic, EMC readback was denied, and energy was not measured. These are
instrumented functional/ownership observations, not performance measurements.

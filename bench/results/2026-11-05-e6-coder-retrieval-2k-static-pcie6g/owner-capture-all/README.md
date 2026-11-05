# Coder retrieval per-layer route and owner capture

This corrected instrumented diagnostic used the same 2,048-token active-ticket
retrieval prompt, 4,096-token context, Coder IQ1_M artifact, static 6 GiB PCIe
complement, and `STRATA_PREFILL_CPU_SHARE=0` as the [timing screen](../README.md).
Adaptive swaps were disabled. It captured one request per backend with the
opt-in MoE trace at every model layer. Timing from these instrumented requests
is excluded.

Both arms returned the exact six-token answer `73192` with identical token IDs.
The trace captured 288 layer/position rows across 48 layers and positions
2,047–2,052 (2,880 routed entries) in each arm. All aligned ordered top-10 ID
lists matched. Owner totals also matched exactly: 86 resident-GPU entries, 793
PCIe entries and 2,001 CPU/file entries. The static profile therefore held the
selected expert work and owner assignment fixed for this request.

An earlier capture inherited default CPU prefill sharing, unlike the timing
runner. Its differing route IDs were caused under a mismatched prefill setting
and are superseded by this corrected capture; do not use that earlier result
for attribution.

The tracked [`result.json`](result.json) contains per-layer/expert owner counts,
route comparison counts and hashes. Raw JSONL traces contain captured CPU
activations and remain local to the Orin workspace; they are not committed.

Reproduce from the project root on the Orin host:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/owner-capture-reproduced-supervisor \
  --sample-clocks --timeout 2400 -- \
  python3 bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/capture_route_owners.py \
  bench/results/2026-11-05-e6-coder-retrieval-2k-static-pcie6g/owner-capture-reproduced
```

Minimum available memory was 14.95 GiB and minimum admission availability was
14.98 GiB, above the six-GiB floor. The existing OOM-kill count remained one.
Clocks were sampled read-only and dynamic, EMC readback was denied, and energy
was not measured. These are instrumented functional/ownership observations,
not performance measurements.

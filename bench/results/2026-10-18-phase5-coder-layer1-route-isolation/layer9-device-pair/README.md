# Device-side layer-9 Coder trace — Orin — 2026-10-19

This randomized mirror-CPU versus GPU-profile pair captures the verifier's
device-side `ffn_x` and `ffn_y` at model layer 9 for all 16 generated positions.
It uses the same 512-token prompt and pinned Coder IQ1_M/MTP artifacts as the
[all-layer route trace](../all-16-positions-three-arm-wildcard/README.md) and
[exact prompt-end GDN comparison](../prefill-gdn-exact-three-arm-checked/README.md).
Both arms returned identical token IDs. The source and binary identity is in
`artifact-identities.json`.

The host route activation matches the verifier's device-side `ffn_x` bitwise
for all 16 rows in both arms. Device `ffn_x` and `ffn_y` differ between arms at
all 16 positions. Their first row is position 511: maximum absolute deltas are
0.00481 for `ffn_x` and 0.000353 for `ffn_y`. Expert IDs and owners still match
there, so the first layer-9 difference is in the activation values before the
router changes its selections. At layer 9, expert IDs differ at positions 517,
518, 520 and 525; owners differ at 517. The paired accepted-prefix analysis
found layer 9 as the first GDN slice divergence at position 511, with layer 2
as the first divergence for positions 512–526. These device rows validate the
layer-9 localization for position 511 and establish that the host trace is
accurate at this layer. They do not identify which earlier decode operation
causes the layer-9 input difference or establish parity through the full
weighted MoE result.

Each arm passed 28-GiB supervision, with minimum host/admission availability
14.39/14.39 GiB and 14.42/14.42 GiB, respectively. Cgroup `high`, `max`, `oom`
and `oom_kill` counters were zero. Clocks were dynamic; energy was not measured
and EMC readback was denied. This is a correctness diagnostic, not a timing
comparison. Phase 5 remains open.

Reproduce from the repository root:

```sh
OUTROOT=bench/results/2026-10-19-phase5-coder-layer9-reproduction \
  bash bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_layer9_device_pair.sh

python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_layer9_device_pair.py \
  --campaign bench/results/2026-10-19-phase5-coder-layer9-reproduction
```

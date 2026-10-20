# Adaptive accepted-state prefix 8 localization — Orin — 2026-10-20

This paired rerun extends the 64-token accepted-prefix test with all-layer
dispatch captures at positions 511–520. It used the same pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M artifacts and the
same candidate binary as the [long-chain run](../reproduction-q8-cuda-input-quantizer-long64/README.md).
The randomized arm order was delayed-control then adaptive-cap8. Both arms ran
the same 512/2,048/512-token prompt sequence, generated 64 tokens per request,
and passed the 28-GiB supervisor with the six-GiB host-availability floor.
This is state and operator localization, not a performance or quality result.

The per-token trace confirms that delayed-control recovery matched initial
short state at every accepted prefix. Adaptive recovery returned identical
token IDs, and full accepted-prefix fingerprints matched through zero-based
prefix 7. Prefix 8, logged at verifier position 519 after token 27,718 was
accepted, is the first state mismatch. GDN ordinals 24–35 differ there; ordinal
24 maps to model layer 32 because QSA layers are every fourth layer and the
preceding layers contain eight QSA blocks.

At that same position, the adaptive all-layer trace first shows a changed MoE
dispatch input at layer 32: relative L2 `1.4294e-5`, maximum absolute delta
`5.2571e-5`. Expert IDs still match at layer 32; owner placement differs.
Expert IDs first differ at layers 37, 45 and 46. The delayed-control trace has
identical activations, expert IDs and owners across all captured positions.
Adaptive activations already differed at some earlier selected positions
while committed state hashes remained equal, so those earlier changes alone do
not locate the persistent-state boundary. This capture narrows the first
observed state mismatch to the layer-32 neighborhood but does not identify a
causal operation.

Both runs passed with zero sampled cgroup low/high/max/OOM/OOM-kill events.
Minimum host/admission availability was 14.32 GiB (delayed-control) and 14.14
GiB (adaptive-cap8); peak scope use was 10.60 and 10.85 GiB. Energy was not
attributed to requests and clocks remained dynamic. `campaign.json`, raw
service logs, per-layer route captures, accepted-prefix fingerprints,
supervisor samples and the derived JSON analysis are retained here.

Reproduce with the model kept under `~/models/strata-orin-validation/`:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261033 --continuations 0 --generated-tokens 64 \
  --capture-moe-positions 511,512,513,514,515,516,517,518,519,520 \
  --output /tmp/coder-adaptive-prefix8

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_selected_positions.py \
  --run /tmp/coder-adaptive-prefix8 \
  --output /tmp/coder-adaptive-prefix8/analysis-selected-positions.json
```

The capture extends correctness diagnostics only. Adaptive CPU Q8_1 migration
remains opt-in and Phase 5 remains open.

# Layer-24 mirror, short-only recovery trace — Orin — 2026-10-20

This randomized same-service pair removes the long request from the earlier
layer-24 selector context-shift probe. It uses three identical 512-token
requests, prompt cache disabled, 12 generated tokens per request, and the
same layer-specific Q8_1 selector through layer 24. The model is the pinned
Coder IQ1_M GGUF at revision `5348543e0147355ac9cbcb031184a3546350988e`; the
current service binary SHA256 is `081212f0…`. Arm order was adaptive-cap8,
then delayed control. Both arms passed supervision; minimum host/admission
availability was 14.10 GiB for adaptive and 14.24 GiB for delayed control.

All three requests returned the same 12 token IDs in both arms. Delayed
control's accepted-prefix fingerprints, per-GDN hashes, routes, owners and
captured activations remained exact across the repeated requests. Adaptive
accepted-state and per-GDN hashes differed at all 12 prefixes from the first
accepted token; the same divergence occurred between both adjacent request
pairs. At verifier position 511, adaptive's first captured MoE-input
activation difference is layer 28. Expert IDs first differ at layers
32/34/35/36/39/43/47; owner placement differs at layers
8/13/16/24/27/28/29/30/33/34/36/39. This shows the state mismatch does not
require a preceding long request. It does not identify a single causal expert
or prove that the layer-24 mirror caused the earlier context shift.

The raw model-layer-4 GDN commit stayed bit-identical across all three adaptive
requests (786,432 recurrent and 30,720 convolution-history values); the
capture's hash matched service GDN ordinal 3 at position 511 in each request.
Delayed control was also bit-identical there. Layer 4 therefore does not
explain this short-only divergence. A separate failed capture attempt selected
layer 3 for raw GDN state; that QSA layer is unsupported for that hook and is
retained in the sibling `layer3-pair` directory.

This is correctness localization only, not a timing or quality comparison and
not a state-migration fix. Phase 5 remains open.

Reproduce from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261077 --sequence short-short-short --continuations 0 \
  --generated-tokens 12 --native-cpu-q8-1-dot \
  'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15,iq3_xxs/iq4_nl@layer=16,iq2_s/iq4_nl@layer=19,iq2_s/iq4_nl@layer=24' \
  --prompt-cache 0 --capture-verify-moe-layer 3 --verify-moe-positions 511 \
  --verify-moe-input-layers all --capture-verify-gdn-layer 4 \
  --verify-gdn-positions 511 --capture-verify-gdn-state-layer 4 \
  --gdn-state-positions 511 --capture-gdn-commit-state-layer 4 \
  --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer24-short-short-short-no-cache-layer3-state4-pair

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_selected_positions.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer24-short-short-short-no-cache-layer3-state4-pair \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer24-short-short-short-no-cache-layer3-state4-pair/selected-position-analysis.json
```

The raw service traces, GDN captures, per-request token IDs, supervisor
telemetry and comparison JSON are retained beside this report.

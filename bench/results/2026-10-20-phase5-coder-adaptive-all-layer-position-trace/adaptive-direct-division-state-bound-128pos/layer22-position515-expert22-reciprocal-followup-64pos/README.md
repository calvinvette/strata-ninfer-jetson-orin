# Layer-22 raw-state follow-up for the expert-22 mirror (64 tokens)

This short follow-up checked whether the 128-token expert-22 campaign's first
accepted-prefix hash difference at position 515/GDN ordinal 17 was already
visible in model layer 22's raw committed recurrent and convolution state.
It repeated seed `20261085` with the same binary and expert-22-only layer-31
reciprocal-SiLU selector, but limited each request to 64 generated tokens.

The same-binary adaptive/control pair passed. Adaptive recovery still differed
on 21/64 tokens, first at index 43; delayed control matched all 64. Raw
layer-22 committed state was bit-exact between each arm's initial and recovery
requests at positions 512–519. Every raw position matched its service GDN
ordinal-17 hash. Thus the shorter chain does not reproduce the layer-22 state
change reported by the 128-token campaign; it does not confirm the 128-token
ordinal-17 mapping or identify the source of the length-dependent transaction
difference. The layer-22 verifier and layer-21→22 boundary captures are retained
for inspection.

Minimum host/admission availability was 14.156 GiB for adaptive and 14.127 GiB
for delayed control; sampled cgroup memory events were zero. Clocks were
observed dynamically, EMC frequency was unavailable, and energy was not
measured. The same-seed 128-token raw layer-22 recapture is the next check.

Reproduce from the repository root with the model remaining under
`~/models/strata-orin-validation/`:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \\
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer22-position515-expert22-reciprocal-followup-64pos \\
  --seed 20261085 --continuations 0 --sequence short-long-short --generated-tokens 64 \\
  --native-cpu-q8-1-dot all --native-cpu-q8-1-reciprocal-silu-layer 31 \\
  --native-cpu-q8-1-reciprocal-silu-expert 22 \\
  --capture-gdn-commit-state-layer 22 --gdn-commit-state-positions 512,513,514,515,516,517,518,519 \\
  --capture-verify-gdn-layer 22 --verify-gdn-positions 515,516,517,518,519 \\
  --capture-verify-gdn-state-layer 22 --gdn-state-positions 515,516,517,518,519 \\
  --capture-boundary-layer 21 --boundary-position 515 --run
```

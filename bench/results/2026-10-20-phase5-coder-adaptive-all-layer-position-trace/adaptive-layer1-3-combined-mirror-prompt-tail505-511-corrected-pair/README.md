# Layer-5 verifier trace across prompt-tail positions 505–511 — Orin — 2026-10-20

This randomized delayed-control/adaptive pair enabled only the combined
layer-1/layer-3 Q8_1 CPU mirrors. It captured all-layer dispatch, layer-5 MoE
and GDN verifier rows at positions 505–511; the single-token pre/post-state
hook captured position 511, and the commit hook captured supported accepted
endpoints 506, 508, 510 and 511.

Delayed control was bit-identical at all selected positions. Adaptive recovery
first differs in the layer-5 GDN `x` field at position 505; subsequent rows
first differ at `h` for 506–507, `x` for 508–509, and `h` for 510–511. The
layer-5 MoE rows also differ, with expert IDs/router weights changing at the
first selected position. At verifier position 511, raw layer-5 pre-state
already differs in 786,409/786,432 recurrent values and 20,480/30,720
convolution-history values. Committed-state comparisons differ at each
captured accepted endpoint. The raw commit at position 511 matches the
service's GDN ordinal-4 hash; the service does not emit one-token accepted
hash rows for the multi-token endpoints 506, 508 and 510.

Both runs passed supervision, with minimum host/admission availability 14.28
GiB adaptive and 14.20 GiB delayed, and zero sampled cgroup pressure/OOM
events. The token split remains at accepted position 517. These captures
narrow the adaptive mismatch to the layer-5 prompt-tail transition but do not
identify its upstream operation. The next target is layer-4 GDN/MoE at the
same positions. No performance claim follows.

The first attempt requested pre/post state at every position 505–511, but the
state hook only supports single-token windows. That failed/unsupported cell is
retained separately and documented in the sibling `...prompt-tail505-511-pair`
directory. The corrected reproduction is:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261055 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 5 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 5 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 5 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 5 --gdn-commit-state-positions 506,508,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-prompt-tail505-511-corrected-pair
```

Campaign order, raw captures, analysis JSON and supervisor telemetry are
retained beside this report.

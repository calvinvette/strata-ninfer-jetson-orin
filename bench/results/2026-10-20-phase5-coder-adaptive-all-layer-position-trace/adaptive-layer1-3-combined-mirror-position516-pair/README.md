# Combined mirror follow-up at the last shared position — Orin — 2026-10-20

This randomized pair repeated the combined layer-1/layer-3 Q8_1 selectors and
captured position 516, the last generated-token position before initial and
recovery output IDs diverged at 517. The pinned Coder IQ1_M artifact and
candidate binary matched the preceding pair. Both supervised arms passed.

At position 516, layer-4 verifier MoE routes, router weights and combined
output were bit-identical across initial/recovery. Layer-4 GDN intermediates
and committed recurrent/convolution state were also exact. Delayed control
remained exact. Adaptive dispatch first differed at layer 5, while its service
GDN hash had already diverged at GDN ordinal 4/model layer 5 from endpoint 511.
This rules out the captured layer-4 MoE/GDN rows as the remaining source at this
position; it does not identify the operation that first changes layer-5 state.

Minimum host/admission availability was 14.34 GiB (adaptive) and 14.24 GiB
(delayed), with zero sampled cgroup pressure/OOM events. No performance claim
is made. The raw captures and exact launch commands are retained here.

Reproduce with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261051 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3' \
  --capture-moe-positions 516 \
  --capture-verify-moe-layer 4 --verify-moe-positions 516 \
  --capture-verify-gdn-layer 4 --verify-gdn-positions 516 \
  --capture-verify-gdn-state-layer 4 --gdn-state-positions 516 \
  --capture-gdn-commit-state-layer 4 --gdn-commit-state-positions 516 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-position516-pair
```

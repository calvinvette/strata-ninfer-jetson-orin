# Combined layer-1/layer-3 mirror pair at position 511 — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used the pinned Coder IQ1_M GGUF
and candidate binary SHA256 `d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`.
Both arms enabled only `iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3` CPU Q8_1
mirrors, then ran the same-service 512→2,048→512 request sequence with 12
generated tokens per request.

At position 511, layer-3 routes, router weights and combined MoE output matched
across adaptive initial/recovery; layer-4 GDN intermediates and raw committed
recurrent/convolution state also matched. The delayed arm remained exact. The
adaptive arm still differed downstream: its first dispatch activation delta
was at layer 5, GDN ordinal 4 was the first changed service hash, and token IDs
first split at accepted position 517 (`819` versus `264`). Thus the two selected
mirrors repair their targeted row and state boundary, but do not establish
adaptive migration parity.

Both supervised runs passed with minimum host/admission availability 14.20 GiB
(adaptive) and 14.22 GiB (delayed), and zero sampled cgroup `high`, `max`, `oom`
or `oom_kill` events. This is a correctness diagnostic, not a performance
result. The position-516 and layer-5 raw-state follow-ups are reported in their
neighboring campaign directories.

Reproduce with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261050 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3' \
  --capture-moe-positions 511 \
  --capture-verify-moe-layer 3 --verify-moe-positions 511 \
  --capture-verify-gdn-layer 4 --verify-gdn-positions 511 \
  --capture-verify-gdn-state-layer 4 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 4 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-combined-mirror-position511-pair
```

Raw captures, exact randomized order, launch commands and supervision telemetry
are retained beside this report.

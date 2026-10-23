# Current-source adaptive accepted-prefix and dispatch comparison

Date: 2026-10-23, Jetson Orin AGX. Phase 5 diagnostic; not a performance
qualification or a Phase 5 exit result.

## Setup

The paired service sequence was `short-long-short`, with 64 generated tokens
per request. It compared delayed adaptation (`adapt-every=100000`) with
cap-8 adaptive swaps (`adapt-every=4`, `adapt-swaps=8`, accepted-only), using
`STRATA_NATIVE_CPU_Q8_1_DOT=all` in both arms. The random arm order was
delayed-control then adaptive-cap8. Both services passed the 28 GiB supervisor
and the 6 GiB host-availability floor. Minimum available memory was 14.37 GiB
in both arms; elapsed service time was 381.0 seconds for control and 377.5
seconds for adaptive. Power was not integrated into this correctness run.

Model: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. Shard SHA-256 values:

- `Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf`: `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad`
- `Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf`: `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`

Candidate binary SHA-256: `afc710def2ad1c0f0905afa015f5cae3e50063b29d7c4fdd62f186ab21a7358d`.
Repository HEAD at run time: `cfb47b20f1553a228242ca17719d3baa6abe679f`.

## Result

A separate same-day 64-token pair without selected-layer capture first showed
cross-arm persistent-state divergence at accepted position 532 in the short
request. This selected-position repeat reproduced the same boundary. Across
the 64-token initial short requests, the first token-ID difference was at
prefix 27 (35/64 IDs differed); accepted-state and GDN hashes first differed
at prefix 21 / absolute position 532 (43/64 prefixes differed). On the
2,048-token request, all 64 token IDs matched, but accepted-state and GDN hashes
first differed at prefix 20 / absolute position 2067 (44/64 prefixes differed).
See [`accepted-prefix-comparison.json`](accepted-prefix-comparison.json).

Within each service, the final 512-token recovery request exactly repeated its
initial short request: zero token, accepted-state, or GDN-hash differences.
Thus the observed change is between the adaptive and delayed configurations;
these runs did not reproduce within-service recovery drift.

Selected MoE dispatch rows were captured at positions 532, 538, and 2067, with
48 layer rows per request-position. At position 532, adaptive and control had
the same token and expert IDs. CPU/GPU ownership first differed at layer 5;
captured MoE input activations remained bit-identical through layer 35, then
first differed at layer 36. At layer 36 and later, 30,719 of 122,880 compared
activation values differed (relative L2 `0.00582`, maximum absolute delta
`0.04686`). At position 2067, input token IDs matched; ownership first differed
at layer 3, numeric input activations first differed at layer 41, and expert
IDs first differed at layer 43. At that position 17,918/122,880 compared
activation values differed (relative L2 `0.00393`, maximum absolute delta
`0.03991`). These associations localize the captured divergence but do not
identify the first owner-specific arithmetic operation or prove a sole cause.

The delayed-control initial and recovery rows were bit-identical at positions
532 and 538. The adaptive initial and recovery request token IDs and accepted
state hashes were exact too; selected owner assignments varied on those two
rows, while all jointly valid captured activation values matched. A few
activation vectors were intentionally unavailable in the selected capture;
those rows are listed in [`focused-comparison.json`](focused-comparison.json).

## Reproduction

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --output bench/results/2026-10-23-phase5-coder-adaptive-divergence-532-2067 \
  --seed 2026102303 --continuations 0 --sequence short-long-short \
  --generated-tokens 64 --native-cpu-q8-1-dot all \
  --capture-moe-positions 532,538,2067 --capture-moe-rows 256 --run
```

The raw service logs, selected dispatch rows, tegrastats and memory samples stay
local with the run output. The two small JSON summaries contain accepted-prefix
hash deltas and selected-layer comparisons for review. The existing
`compare_selected_positions.py` helper rejects a selected position with only
one captured request block (position 2067); the 48 rows were checked and
compared directly for this report. That analyzer limitation does not indicate
a service or capture failure. This is one model, binary, prompt sequence, and
hardware run; it makes no performance or energy claim and does not close
Phase 5.

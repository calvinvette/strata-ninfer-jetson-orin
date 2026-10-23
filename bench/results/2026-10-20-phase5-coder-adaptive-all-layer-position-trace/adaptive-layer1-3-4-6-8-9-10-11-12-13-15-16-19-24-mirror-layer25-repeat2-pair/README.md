# Layer-24 mirror context-shift repeat — Orin — 2026-10-20

This randomized delayed-control/adaptive pair repeated the selector and
512/2,048/512 workload from the preceding layer-24 probe with seed `20261076`.
It used the pinned Coder **IQ1_M** GGUF from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. The
adaptive arm adds the layer-24 IQ2_S/IQ4_NL rule to the earlier layer-specific
CPU Q8_1 rules. Both services generated 12 tokens per request and completed
under separate 28-GiB supervisors.

The prior context shift reproduced. Delayed-control initial/recovery had the
same 12 token IDs and all selected activations, routes, owners and accepted
state matched. In adaptive-cap8, all 12 recovery token IDs differed from the
initial short request; accepted-state and GDN hashes differed at every shared
prefix. At each selected position 505–511, the first captured activation
difference was layer 3. This is upstream of the layer-24 target, so this pair
does not attribute the difference to expert 173 or qualify its mirror as a
fix. The layer-24 accepted commit at position 511 differed in all 786,432
recurrent values and all 30,720 convolution-history values between initial
and recovery. The raw-state comparison is retained in
`layer24-state-analysis.json`; selected dispatch/activation comparisons are
in `selected-position-analysis.json`.

Seeing the same layer-3 first difference in two randomized pairs makes a
cross-request adaptive-history effect plausible, but does not prove its source.
The layer-24 selector may alter the preceding request history used by adaptive
residency; state reset and history controls are needed to separate that from
other sources. Preserve the finding as an inconclusive layer-24 localization.

Both arms passed supervision. Minimum host and admission availability was
14.23 GiB for delayed-control and 14.27 GiB for adaptive-cap8; both stayed above
the six-GiB floor with zero cgroup `high`, `max`, `oom`, and `oom_kill` events.
Clocks were observed but not controlled; energy was not attributed to requests.
This is correctness diagnostic evidence, not a timing or quality comparison.

Reproduce from the repository root:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261076 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15,iq3_xxs/iq4_nl@layer=16,iq2_s/iq4_nl@layer=19,iq2_s/iq4_nl@layer=24' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 25 --verify-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-layer 24 --verify-gdn-positions 505,506,507,508,509,510,511 \
  --capture-verify-gdn-state-layer 24 --gdn-state-positions 511 \
  --capture-gdn-commit-state-layer 24 --gdn-commit-state-positions 511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer25-repeat2-pair
```

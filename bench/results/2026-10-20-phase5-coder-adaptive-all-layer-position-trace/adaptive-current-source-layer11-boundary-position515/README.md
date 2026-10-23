# Layer-11 boundary and layer-12 GDN at position 515

This follow-up targets the earliest difference from the adjacent all-layer
verifier-input capture. It used the same Coder IQ1_M artifact, current candidate
binary, short/long/short sequence, and 12 generated tokens per request. Seed:
`2026102232`; binary SHA256:
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`; source
tree HEAD `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`. Both supervised arms
passed.

Initial short-request captures matched bitwise between arms across every
layer-11 boundary field and layer-12 pre/post-GDN state. Delayed control also
reproduced all selected layer-11 boundary fields and layer-12 state exactly
after the long request. Adaptive recovery differed in one layer-11 boundary
component: all 2,560 `bo` values changed (maximum absolute difference
`2.8992e-6`, relative L2 `1.0218e-4`); `R` and `inj2` remained bit-identical.
The next-layer read then differed in 7,974 values of `R` and 7,900 values of
`xn`. Layer-12 pre-GDN state remained exact, while post-GDN state differed in
793,357/817,152 values (maximum absolute difference `0.00090820`, relative L2
`0.00010004`). Adaptive recovery emitted the same short-request tokens but
changed accepted-state fingerprints.

Together with the all-layer input trace, the earliest observed difference is
the layer-11 `bo` boundary, immediately before layer 12. The evidence narrows
the onset to that output component for this request and candidate. It does not
identify which layer-11 computation or adaptive residency decision perturbs
`bo`, and it does not establish a broader numerical or quality bound. No
runtime source change was made.

Minimum host/admission availability was 14.17 GiB for delayed control and
14.28 GiB for adaptive; cgroup memory events were zero. See `campaign.json`,
arm telemetry, per-arm boundary summaries, `initial-cross-arm-boundary.json`,
and `gdn-layer12-summary.json`. `SHA256SUMS` covers raw captures and summaries.

Reproduction command:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 2026102232 --continuations 0 --sequence short-long-short \
  --generated-tokens 12 --native-cpu-q8-1-dot all \
  --capture-boundary-layer 11 --boundary-position 515 \
  --capture-verify-gdn-layer 12 --verify-gdn-positions 515 \
  --capture-verify-gdn-state-layer 12 --gdn-state-positions 515 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-source-layer11-boundary-position515
```

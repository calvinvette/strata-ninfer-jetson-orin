# Position-512 prefill and accepted-state trace — Orin — 2026-10-20

This paired diagnostic checks whether the layer-2 GDN state already differs
after the repeated 505-token prompt, then captures the state and dispatch at
position 512. It uses the Coder IQ1_M artifact at revision
`5348543e0147355ac9cbcb031184a3546350988e`, the current candidate binary
`6e4b89f7d0979dd0d16eb000c238aa837d5c990dbe54033dada9a479a93fcd38`, and the
opt-in `iq3_xxs/iq4_nl@layer=31` CPU Q8_1 mirror. The adaptive arm ran before
the delayed-control arm. Both were supervised separately with the existing
six-GiB host-availability floor.

At layer 2, all eight prefill boundaries (64 through 505 tokens) had matching
full-width state hashes between the initial and recovery short requests in
each arm. The raw end-of-prefill state was also bit-identical across arms and
requests: recurrent matrix and convolution history SHA256
`d66e61d681cf44c2d2577ba210665af7fbfc1b3d333db17b40b25a884f4be057`. This
rules out a layer-2 GDN prefill mismatch for this repeated prompt and pair.

At selected verifier position 512, output token IDs were identical across the
initial and recovery requests in both arms. The delayed-control layer-2
pre/post verifier state was bit-identical between requests. In the adaptive
arm, the pre-state differed in 786,035/786,432 recurrent values (relative L2
`0.00139038`) and 30,711/30,720 convolution values (relative L2 `0.00255206`).
The committed post-state differed in 786,044 recurrent values (relative L2
`0.00185596`) and 30,711 convolution values (relative L2 `0.00270442`). The
raw committed-state hashes matched the service's per-layer state hashes.

The same-position dispatch trace locates the first observed owner change at
model layer 1: expert IDs and its input activation matched, while two routed
experts changed owner. The next layer-2 dispatch activation differed in all
2,560 values (relative L2 `0.00390268`); layer-2 expert IDs also changed. The
layer-2 verifier intermediate capture first differs in `x`, consistent with
that dispatch trace. The delayed-control dispatch and GDN verifier captures
were bit-identical across initial and recovery requests. This localizes the
adaptive discrepancy after prompt prefill and before/at layer-1 owner-dependent
work, but does not establish which expert arithmetic or transaction operation
causes the state change. A separate position-512 layer-1 verifier-parts pair
is retained alongside this report to examine that boundary.

Both supervised runs passed. Minimum host and admission availability was
14.18 GiB for adaptive and 14.29 GiB for delayed control; sampled cgroup event
counters remained zero. This is a correctness-localization pair, not a
performance or quality comparison.

Reproduce the paired capture from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261042 --continuations 0 --generated-tokens 12 \
  --capture-moe-positions 512 \
  --capture-verify-gdn-layer 2 --verify-gdn-positions 512 \
  --capture-verify-gdn-state-layer 2 --gdn-state-positions 512 \
  --capture-gdn-commit-state-layer 2 --gdn-commit-state-positions 512 \
  --trace-prefill-gdn-state-layer 2 \
  --native-cpu-q8-1-dot 'iq3_xxs/iq4_nl@layer=31' \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-prefill-gdn2

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_prefill_gdn_state_pair.py \
  --service-log bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-prefill-gdn2/adaptive-cap8/result/service.log \
  --state-dump bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-position512-prefill-gdn2/adaptive-cap8/result/prefill-gdn-state.bin \
  --layer 2 --output /tmp/prefill-adaptive.json
```

The raw service logs, selected-position captures, GDN intermediates, verifier
and commit-state dumps, per-arm analyses, supervisor telemetry and campaign
metadata are retained in this directory. The comparison scripts validate raw
state against service hashes where supported.

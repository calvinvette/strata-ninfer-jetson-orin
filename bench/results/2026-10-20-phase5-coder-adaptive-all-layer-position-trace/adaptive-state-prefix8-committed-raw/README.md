# Accepted-prefix 8 committed GDN state capture — Orin — 2026-10-20

This paired rerun captured the serving session's committed layer-32 GDN state
at accepted endpoints 518, 519 and 520, after the 64-token trace found adaptive
state divergence at prefix 8. It used the pinned Coder IQ1_M revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary SHA256
`14afd1a4b953e176a88d7812bddcdf2beb65944bb5795beaf0f37e5834a496aa`. Both
supervised arms passed; the adaptive arm was first in this randomized pair.

The raw committed arrays confirm the accepted-prefix trace. In adaptive
recovery, the 786,432-float recurrent matrix and 30,720-float convolution
history were bit-identical to initial short state at position 518. At position
519, 564,534 recurrent values differed (relative L2 `1.28332e-7`, maximum
absolute delta `8.94070e-8`), while all convolution-history values remained
exact. At position 520, 538,720 recurrent values differed (relative L2
`1.15621e-7`); convolution history was still exact. Delayed-control committed
arrays were bit-identical at all three positions. Each raw layer-32 snapshot's
FNV1a hash matches the per-layer GDN hash at the same accepted-prefix position
in `service.log`, confirming the raw capture is aligned to the serving state
fingerprint.

This directly confirms that the adaptive persistent-state difference is a
small, widespread change in the layer-32 recurrent matrix, not convolution
history. Together with the [layer-31 expert capture](../adaptive-state-prefix8-verifier-capture/README.md),
which found an owner-dependent expert-22 contribution change and a changed
layer-32 GDN input, the evidence strongly localizes the first observed state
drift to that boundary. It does not establish an accuracy winner or qualify
other models and formats.

The 28-GiB supervisors recorded zero sampled cgroup low/high/max/OOM/OOM-kill
events. Minimum host/admission availability was 14.26 GiB for adaptive and
14.22 GiB for delayed control; peak scope use was 10.64 and 10.93 GiB. Runs
took 309.3 and 311.3 seconds. Clocks remained dynamic and energy was not
request-attributed. Raw captures, service logs, all-layer traces, comparator
results and supervisor samples are retained here.

Reproduce from the repository root, keeping the model under
`~/models/strata-orin-validation/`:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261035 --continuations 0 --generated-tokens 64 \
  --capture-gdn-commit-state-layer 32 --gdn-commit-state-positions 518,519,520 \
  --output /tmp/coder-prefix8-committed

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_gdn_commit_state_trace.py \
  --state-dump /tmp/coder-prefix8-committed/adaptive-cap8/result/gdn-commit-state.bin \
  --service-log /tmp/coder-prefix8-committed/adaptive-cap8/result/service.log \
  --gdn-ordinal 24 --layer 32 \
  --output /tmp/coder-prefix8-committed/adaptive-commit-state.json
```

The comparator also passes on delayed control. Adaptive migration remains
opt-in; Phase 5 remains open for state-transition isolation and broader
qualification.

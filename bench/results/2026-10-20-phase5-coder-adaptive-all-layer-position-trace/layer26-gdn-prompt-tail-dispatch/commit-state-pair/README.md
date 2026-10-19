# Layer-26 accepted GDN commit state: delayed versus adaptive — Orin — 2026-10-20

The delayed-control arm was rerun with an opt-in raw state capture at accepted
GDN commit position 506. Its initial and recovery short requests had the same
token ID at the endpoint and identical complete layer-26 state: 0/786,432
recurrent values differed and 0/30,720 convolution-history values differed.
The initial delayed state also matched the initial adaptive state byte-for-byte.

The adaptive arm's existing raw commit trace at the same endpoint shows
786,389/786,432 recurrent values and 10,240/30,720 convolution-history values
differing between initial and recovery. The delayed recovery state matches the
adaptive initial state, while the adaptive recovery state carries this delta.
Thus the first measured accepted GDN endpoint divergence at position 506 is
specific to the adaptive arm in this paired workload. This corroborates the
route trace: delayed recovery stays exact, while adaptive recovery first shows
a layer-26 activation difference at prompt-tail positions 505 and 506.

This still does not identify which transfer, scheduling decision, verifier
operation, or earlier accepted transition introduces the state change. It is
an endpoint comparison, not a per-token operation trace.

The supervised delayed-control run passed in 208.0 seconds with 14.38 GiB
minimum host/admission availability and zero cgroup low/high/max/OOM events.
The raw 3.2 MiB GDN state dump remains outside Git at
`~/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-delayed-control-layer26-commit-position-506-2026-10-20.bin`.
The adaptive raw capture is retained at
`~/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-layer26-commit-positions-500-514-2026-10-20.bin`.
`analysis.json` contains the cross-arm counts and relative L2 values without
embedding either raw state array.

Reproduce the delayed capture on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/commit-state-pair/supervisor \
    --timeout 1200 --interval 1 --sample-clocks -- \
    python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
      --adapt-every 100000 --adapt-swaps 96 --capture-gdn-commit-state-layer 26 \
      --gdn-commit-state-positions 506 \
      --gdn-commit-state-output "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-delayed-control-layer26-commit-position-506-2026-10-20.bin" \
      --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/commit-state-pair/run

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_gdn_commit_state_arms.py \
  --delayed-state-dump "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-delayed-control-layer26-commit-position-506-2026-10-20.bin" \
  --adaptive-state-dump "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-layer26-commit-positions-500-514-2026-10-20.bin" \
  --layer 26 --position 506 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/commit-state-pair/analysis.json
```

Phase 5 remains open.

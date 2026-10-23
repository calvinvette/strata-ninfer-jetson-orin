# Layer-31 expert-22 reciprocal-SiLU mirror: rejected

## Question and decision

The layer-wide reciprocal-SiLU trial changed more layer-31 CPU rows than the
expert-22 owner capture implicated. This follow-up added an opt-in expert-ID
filter and selected only model layer 31, expert 22. It repeated the same
short→long→short Coder IQ1_M adaptive recovery sequence, with delayed control,
raw layer-32 committed state, accepted-prefix hashes, token history, and
layer-31 verifier inputs/routes/rows captured.

**Decision: reject this as a state-recovery correction.** The adaptive arm still
failed, and its first accepted-prefix GDN hash difference moved earlier than in
the direct-division reference. Keep both reciprocal selectors opt-in and
default-off. This run supplies no performance claim.

## Setup

- Orin AGX; current-source binary SHA256
  `0a5f9b0dd9ac96320986a67ba9daf5e6abe6ac570500ea77c36a5ca52919996c`.
- Coder GGUF IQ1_M, repository revision
  `5348543e0147355ac9cbcb031184a3546350988e`; shard hashes, prompt hashes,
  request token IDs and source identities are recorded in `campaign.json` and
  `adaptive-cap8/result/analysis.json`.
- Same-binary randomized pair, seed `20261085`, 128 generated tokens per
  short→long→short request sequence, MTP2, CPU Q8_1 dot selector `all`.
- Treatment selected reciprocal-SiLU only for model layer 31 / expert 22.
  Delayed control used the same source and inputs with adaptation delayed.
- Both arms passed. Minimum host/admission availability was 14.126 GiB for
  adaptive and 14.097 GiB for delayed control; sampled cgroup memory events
  were zero. Clocks remained dynamically managed and observed; EMC frequency
  was unavailable. Energy was not measured.
- The native-expert synthetic selector check accepted layer 31/expert 22 and
  passed with zero oracle failures; a malformed expert selector failed clearly
  with “must be a non-negative expert number.” The service pair above is the
  evidence for applying the filter to routed jobs.

Reproduce from the repository root with the pinned local model still under
`~/models/strata-orin-validation/`:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/layer31-expert22-reciprocal-silu-state-bound-128pos \
  --seed 20261085 --continuations 0 --sequence short-long-short --generated-tokens 128 \
  --native-cpu-q8-1-dot all --native-cpu-q8-1-reciprocal-silu-layer 31 \
  --native-cpu-q8-1-reciprocal-silu-expert 22 \
  --capture-gdn-commit-state-layer 32 \
  --gdn-commit-state-positions 515,516,517,518,519,534,557,558,574,638 \
  --capture-verify-moe-layer 31 --verify-moe-positions 515,516,517,518,519 \
  --verify-moe-input-layers same --capture-verify-gdn-layer 32 \
  --verify-gdn-positions 515,516,517,518,519 --capture-verify-gdn-state-layer 32 \
  --gdn-state-positions 515,516,517,518,519 --capture-boundary-layer 31 \
  --boundary-position 519 --run
```

## Results

Delayed control reproduced all 128 recovery tokens and exact captured
layer-32 state. The expert-22 adaptive arm differed on 85/128 recovery tokens,
first at output index 43. For context, the separate direct-division reference
pair (seed `20261082`) first differed at index 47 and differed on 73/128; it is
not a same-seed direct comparison. The earlier layer-wide reciprocal trial
(seed `20261084`) first differed at index 6 and differed on 121/128. These
single-pair counts do not estimate a general effect, but neither reciprocal
trial qualifies as a recovery fix.

The accepted-prefix scan of all 36 per-layer GDN hashes found the adaptive
arm's first initial-versus-recovery hash difference at absolute position 515,
GDN ordinal 17. The direct-division reference's first difference was position
519, ordinal 24. The delayed control had no token, state, or GDN hash
mismatches. Raw layer-32 captures at positions 515–519 matched the service's
accepted-prefix hashes exactly. At position 515 the treatment's layer-32
recurrent state differed in 786,391/786,432 values (relative L2 `0.001685`)
and convolution history differed in 10,240/30,720 values (relative L2
`0.006613`); delayed control was bit-exact there. The captured treatment
therefore still had a large state transition before the previously localized
position-519 event.

The captured layer-31 verifier analysis shows initial-versus-recovery changes
in route weights, expert parts and combined outputs at positions 515–519. Those
are within-arm sequence comparisons, so they do not identify which expert row
caused the new earlier state difference. The expert-ID filter ensures only
expert 22 receives the reciprocal expression when the selector is active; it
does not establish that this one row explains the whole transaction outcome.
The CPU/CUDA row-level oracle from the earlier position-519 capture remains
isolated evidence, not a persistent-state correction.

Raw captures and summaries are under `adaptive-cap8/result/` and
`delayed-control/result/`; `accepted-prefix-analysis.json` compares all 128
accepted positions to the direct-division reference and each delayed control.
The broader layer-wide rejected experiment is in the sibling
`layer31-reciprocal-silu-state-bound-128pos/` directory.

## Next step

Return to Phase 5's state-transaction boundary. Trace the adaptive accepted
prefix through the first changed hash at position 515/GDN ordinal 17, including
state before and after the long-request restoration and the earlier GDN
ordinals. Keep token history and every captured state hash paired with a raw
state check. Do not promote either reciprocal-SiLU selector or infer a
layer-31-only cause from the owner capture until a held-out full-chain test
passes.

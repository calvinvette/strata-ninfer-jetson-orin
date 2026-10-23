# Layer-22 raw-state recapture for the expert-22 mirror (128 tokens)

This same-seed follow-up resolves whether the expert-22 campaign's first
accepted-prefix hash difference at position 515/GDN ordinal 17 belongs to
model layer 22. It repeated seed `20261085` with the same binary and layer-31,
expert-22 reciprocal-SiLU selector, captured committed layer-22 state at
positions 512–519, and recorded accepted-prefix verifier and boundary state.

Both arms passed. In adaptive recovery, layer-22 recurrent and convolution
state first differ from that arm's initial request at position 515. Positions
512–514 are bit-exact. The raw layer-22 hashes match service GDN ordinal 17 at
every captured position 512–519, confirming that the earlier hash-only result
maps to layer 22. Delayed control is bit-exact at all eight positions. The
adaptive arm's accepted-token mismatch still begins at recovery index 43, so
this mirror is not a recovery correction. The separate 64-token pair remains
exact in raw layer-22 state through position 519, showing that this state
change depends on request length or subsequent accepted-token history.

Adaptive and delayed-control minimum host/admission availability were 14.135
and 14.093 GiB. Sampled cgroup memory events were zero. Clocks were observed
dynamically, EMC frequency was unavailable, and energy was not measured. Both
arms took about 600 seconds. The paired run's model, quantization, binary,
source and shard identities are recorded in `campaign.json`.

Raw analysis files are `adaptive-cap8/result/gdn-raw-analysis.json` and
`delayed-control/result/gdn-raw-analysis.json`. They confirm raw-to-service
hash matches at each captured position. The accepted-prefix, raw state, layer
21→22 boundary and verifier captures remain alongside the campaign for further
upstream tracing.

A follow-up parse of the captured layer-21→22 verifier boundary narrows the
upstream trace. In adaptive recovery at position 515, `after_layer_bo` already
differs in all 2,560 values (relative L2 `0.002059`); `after_layer_R` and
`after_layer_inj2` remain bit-exact. The `before_next_read_bo` field carries
the same difference. The layer-22 GDN input and post-state then differ, while
the delayed-control fields remain exact. Parsed records are in each arm's
`result/layer21-boundary-analysis.json`. This points the next localization at
layer 21's input/compute path, without yet identifying which earlier operation
caused the changed output.

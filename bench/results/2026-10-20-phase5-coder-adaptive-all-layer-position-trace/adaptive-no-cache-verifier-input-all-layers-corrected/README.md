# All-layer verifier input trace at the first adaptive state mismatch

This supervised correctness pair used three identical no-cache short requests
(initial/intermediate/recovery) on the Coder `IQ1_M` model from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. The adaptive arm used a cap-8
migration schedule; the control delayed adaptation. The Coder shard checksums
and executable SHA-256 are in `campaign.json`. Both arms passed. Minimum
available host/admission memory was 14.197 GiB for adaptive and 14.103 GiB for
control; the 28-GiB supervisor recorded no OOM or cgroup pressure event.
Adaptive recovery differed from initial output at 6/12 token IDs; delayed
control matched at all 12.

The opt-in verifier input diagnostic captured all 48 layer inputs at absolute
position 511 for each of the three requests (144 records per arm, each a
2,560-float tensor). Its checked parser validates record headers, order, token
identity, finite values and exact coverage. In delayed control, all layer
inputs matched across all requests. In adaptive mode, initial and intermediate
matched through layer 33; their first difference was layer 34. Intermediate
and recovery first differed at layer 12. Differences continued through later
layers. These locations align with the first changed per-GDN accepted-state
hashes in `accepted-prefix-analysis.json`: ordinal 26 maps to model layer 34;
ordinal 9 maps to model layer 12.

This localizes the verifier activation change to those model-layer boundaries
for this sequence. It does not prove whether a changed GDN pre-state, a
transaction write/restore, or another earlier operation causes it. The next
check is a direct pre/post raw-state capture at model layers 12 and 34,
validated against the corresponding service GDN hashes. No performance claim
is made; Phase 5 remains open.

The preceding `adaptive-no-cache-verifier-input-all-layers/` pair is retained
as an invalid diagnostic cell: the workload arms passed, but the first version
of the input hook applied the layer destination offset to the source tensor.
The analyzer found non-finite values and rejected the capture. The corrected
source and this rerun use separate artifacts; do not use the earlier input
trace for inference.

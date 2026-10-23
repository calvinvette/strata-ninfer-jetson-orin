# Adaptive-choice trace for the layer-21 expert-132 ownership change

This is a same-seed repeat of the layer-31/expert-22 reciprocal-SiLU pair with
`STRATA_TRACE_ADAPT=1`. It adds round-by-round adaptive choices to the same
layer-21 position-515 capture, using the Coder IQ1_M model, binary
`0a5f9b0d…1996c`, seed `20261085`, and 128-token short/long/short sequence.

The adaptive trace records that at accepted position 598, after 88 accepted
verifier rows, round 88 selects `21:132>12`: bring expert 132 into layer 21's
GPU residency and evict expert 12. At the earlier position 515 in the initial
short request, expert 132 is still CPU-owned; in recovery at position 515, it
is GPU-owned. The row/output comparison reproduces the prior result: expert
132 changes in all 2,560 values (relative L2 `0.014265`), the combined layer-21
MoE output changes by relative L2 `0.002059`, and layer 22 is the first changed
verifier MoE input (relative L2 `0.0009497`). Delayed control keeps expert 132
on CPU and is exact in all captured layer-21 and all-layer input records.

This connects the observed recovery owner to an explicit accepted-only
adaptation choice. In the paired same-seed direct-division control without the
selector, expert 132 stayed CPU-owned and layer-21 output remained exact at
position 515. The selector association is therefore reproduced; broader
prompt/seed validation and the mechanism by which selector output changes
later adaptation statistics remain open. The selector remains a rejected
recovery correction: adaptive recovery first differs at output index 43
(85/128), versus index 47 (73/128) without it. Both delayed controls are exact.

Both arms passed. Minimum host/admission availability was 14.142 GiB adaptive
and 14.196 GiB delayed control; sampled cgroup memory events were zero.
Frequencies were observed dynamically, EMC frequency was unavailable due to
debugfs permissions, and energy was not measured. Elapsed times were 622.1 and
602.6 seconds.

`adapt-choice-trace.json` parses every adaptive choice and records the round-
88 event. `analyze_moe_inputs.py` checks raw verifier inputs; `selected-position-analysis.json`, each arm's `layer21-moe-analysis.json`, and `layer20-boundary-analysis.json` hold the remaining parsed evidence. Raw service logs and binary captures remain alongside them.

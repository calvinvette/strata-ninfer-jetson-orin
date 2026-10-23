# Distinct retrieval prompt: layer-21 selector comparison

This pair uses the existing held-out retrieval workload from the Phase 6
cache/context confirmation, capped to its final 2,048 encoded tokens. The
separate 512-token short prompt is the tail of that suffix, so the selected
state boundary remains at position 515. The prompt file identity, selected
entry, source token count (7,501), suffix limit (2,048), and actual token hashes
are recorded in `campaign.json` and each arm's `analysis.json`.

Both arms passed with at least 14.172 GiB host/admission availability and zero
sampled cgroup memory events. With the layer-31/expert-22 selector, adaptive
recovery differed on 19 tokens; delayed control matched. This short-answer
workload generated 32 tokens for the initial short request and 47 for the long
request, so it did not reach the prior round-88 event. At layer 21 / position
515, expert 132 is GPU-owned in both initial and recovery captures. The
first-layer-21 input difference appears at model layer 22, while expert rows
for ranks 0 and 3 change. The delayed control is exact.

The [same-workload direct-division pair](../layer21-position515-heldout-direct-division-128pos/README.md)
shows the same 19 adaptive token differences, first GDN divergence at ordinal
0, identical layer-21 combined-output hashes and rank-0/rank-3 expert outputs,
and the same GPU ownership for expert 132. Thus this prompt exposes adaptive
recovery drift, but the sampled layer-21 behavior is not selector-specific.
This is a genuine workload change, but its short answers do not provide enough
accepted rows to repeat the round-88 owner transition. A separate open-response
workload is prepared for a deeper accepted chain.

The selector pair ran in 313.2 seconds for delayed control and 308.0 seconds
for adaptive, with minimum available host memory 14.172/14.218 GiB. Frequencies
were observed dynamically, EMC was unavailable, and energy was not measured.
These are correctness captures, not serving-performance measurements.

`heldout-layer21-selector-vs-direct-division.json` consolidates both pairs;
`selected-position-analysis.json`, `adapt-choice-trace.json`,
`moe-input-analysis.json`, and the per-arm layer-20/21 analyses retain the
parsed evidence. Raw captures and service logs remain in each campaign folder.

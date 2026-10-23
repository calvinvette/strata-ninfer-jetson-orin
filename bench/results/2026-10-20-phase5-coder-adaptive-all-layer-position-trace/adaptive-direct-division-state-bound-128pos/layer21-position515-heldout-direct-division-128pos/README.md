# Distinct retrieval prompt without the reciprocal-SiLU selector

This paired direct-division control uses the same Phase 6 held-out retrieval
workload, same 2,048-token suffix, 512-token short prompt, seed, binary, and
position-515 captures as the [selector pair](../layer21-position515-expert22-heldout-prompt-128pos/README.md).
Both arms passed with at least 14.123 GiB available host/admission memory and
zero sampled cgroup events. The adaptive arm differed on 19 recovery tokens,
first at GDN ordinal 0; delayed control was exact. At layer 21, expert 132
remained GPU-owned in both initial and recovery requests. Expert rows at ranks
0 and 3 and the combined MoE output changed in adaptive recovery, while routes,
router weights, rank-7 expert 132, and the shared expert matched.

The selector and direct-division adaptive captures have identical layer-21
combined-output and rank-0/rank-3 output hashes, with the same first changed
MoE input (layer 22). This shows the observed drift for this prompt is not
specific to the selector at the captured boundary. See the consolidated
[`heldout-layer21-selector-vs-direct-division.json`](../heldout-layer21-selector-vs-direct-division.json).

The direct-division pair took 315.4 seconds for delayed control and 336.2
seconds for adaptive; minimum host/admission availability was 14.157/14.123
GiB. Frequencies were observed dynamically, EMC was unavailable, and energy
was not measured. `campaign.json` and `analysis.json` record the exact prompt
source hash and token lengths; parsed captures are stored per arm.

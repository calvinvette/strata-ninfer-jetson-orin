# Layer-21 owner control without the reciprocal-SiLU selector

This same-seed control repeats the layer-21 position-515 verifier capture with
the layer-31/expert-22 reciprocal-SiLU selector unset. It uses the same Coder
IQ1_M model, binary, seed `20261085`, short/long/short request sequence,
128-token generation cap, and capture geometry as the paired
[selector run](../layer21-position515-expert22-chain-128pos/README.md).

Both arms passed. In adaptive recovery, layer-21 routes, router weights, all
expert rows, and combined output at position 515 are exact between the initial
and recovery requests. Expert 132 stays on CPU. All 48 captured verifier MoE
inputs and the layer-20 boundary are also exact. Delayed control is exact in
these captures as well. This differs from the selector run, where expert 132
moved CPU→GPU in adaptive recovery, its row changed at relative L2 `0.014265`,
and the layer-21 combined output changed at relative L2 `0.002059`. The
contrast makes the owner migration selector-associated in these same-seed
campaigns; it does not establish a general causal mechanism from one pair.

As in the earlier direct-division adaptive reference, token recovery is still
not exact: adaptive output first differs at index 47 (73/128); delayed control
matches all 128 tokens. The first accepted-prefix GDN difference is ordinal 24,
whereas the selector run first differs at ordinal 17. Neither candidate is a
recovery correction.

Minimum host/admission availability was 14.157 GiB adaptive and 14.248 GiB
delayed control, with zero sampled cgroup memory events. Frequencies were
observed dynamically; EMC frequency was unavailable due to debugfs permissions
and energy was not measured. Elapsed times were 599.4 and 602.0 seconds. The
campaign records the pinned model, binary, runner, and shard identities.

Raw captures and parsed files are retained in each arm. `selected-position-analysis.json`
compares accepted prefixes and selected routes/owners, each arm's
`layer21-moe-analysis.json` compares routes, expert rows and combined output,
and `moe-input-analysis.json` directly compares all 48 raw verifier inputs.

# Accepted-prefix GDN capture smoke checks

Added opt-in harness controls for the runtime's existing all-GDN-layer commit
capture and its existing end-of-prefill GDN snapshot. The smoke checks used a
2K retrieval workload with a configured 262,144-token context. This validates
the capture path and is not a long-context qualification.

All three paired checks returned the exact expected answer, identical 47 token
IDs, and identical residency fingerprints between Strata and strict NInfer.
All three still reported differences in final `gdn`, `tail`, `pooled`,
`pooled_full`, and `kv` state. The baseline 2K result in the sibling `run/`
directory used an 8,192-token configured context; it is not a matched control
for these 262,144-context captures.

The end-of-prefill snapshot at boundary 2041 was bitwise equal across engines
for model layer 4 in one pair and layer 6 in another pair. The all-layer commit
capture at accepted position 2093 emitted all 36 GDN layers (117,671,616 bytes
per arm). The first material cross-engine difference (>1e-4 relative L2) was
model layer 6 in the layer-4 snapshot pair (`3.098e-3`), but model layer 4 in
the layer-6 snapshot pair (`3.496e-3`) and in the commit-only pair
(`3.496e-3`). The commit-only and layer-6 pair had closely matching per-layer
state differences; the layer-4 pair differed. This variability prevents
assigning a stable earliest split or attributing it to prompt processing versus
decode. The snapshots cover only the selected prefill layer, not the complete
prefill state at every layer.

Each pair took about 305 seconds. Minimum available memory was 7.11–7.42 GiB;
peak swap was 1.06–1.59 GiB, with zero sampled OOM events. The three short
smokes are diagnostic only. The all-layer accepted-prefix and prefill capture
paths are now available for the planned 160K check. Raw files and comparator
JSON remain local under this directory and its sibling `gdn-capture-cli-layer6/`
and `gdn-commit-only-smoke/` directories.

# Repeated layer-27/28 capture — Orin — 2026-10-20

This repeats the [seed 20261078 layer-27/28 pair](../adaptive-layer24-short-short-short-no-cache-layer27-state28-pair/README.md)
with seed 20261079, the same fixed prompts, greedy decoding, selector, and
capture settings. Both supervised arms passed. Minimum host/admission
availability was 14.30 GiB adaptive and 14.13 GiB delayed control; no cgroup
memory events were recorded.

This is a deterministic reproducibility check, not an independent randomized
workload sample. Both arms emitted the same token IDs as the earlier pair. In
the adaptive arm, expert 175 again changes CPU-to-CUDA at layer 27; the service
rows match the same-input CPU and CUDA oracles, and layer-28 `x` is the first
changed GDN intermediate. The committed layer-28 state differs from the first
request and matches the service hash for all three captures. Delayed control
remains exact. The dispatch, verifier-input, expert-part, combined-output and
committed-state captures are byte-identical to seed 20261078.

The row/oracle and layer-28 intermediate comparisons are retained in
`layer27-analysis.json`, `adaptive-layer28-intermediate-analysis.json` and
`delayed-layer28-intermediate-analysis.json`. Phase 5 remains open.

# Generated-position trace after repeated short requests — Orin — 2026-10-20

This randomized same-service short/short/short pair captures all-layer MoE
dispatch inputs at generated positions 512–523 for the initial, intermediate
and recovery requests. Each request used the same 512-token prompt and a
12-token generation limit. Position 523 has no dispatch record because the
last emitted token has no following model pass; positions 512–522 are present
for all three requests. The absent terminal capture is retained as an
unsupported cell, not treated as a pass.

Both arms passed the 28-GiB supervisor. Minimum host/admission availability
was 14.13 GiB for adaptive and 14.19 GiB for delayed control; sampled cgroup
memory events were zero. The model and binary identities are recorded in
`campaign.json`; the model is the pinned Coder IQ1_M GGUF and PLE pack.

All generated token IDs matched across the three requests in both arms.
Delayed-control state and GDN fingerprints were exact between every request.
Adaptive state first differed at accepted prefix 4 between the initial and
intermediate request, then matched exactly between intermediate and recovery.
The selected generated-position trace's first initial-to-intermediate input
activation difference is at layer 27, position 512; expert IDs are still
identical, while owner placement differs at layers 26 and 27. Across positions
512–522, the comparator preserves each request transition's activation, route
ID and owner differences. This narrows the first observed transition but does
not prove a single owner row caused the persistent-state difference.

The pair is correctness localization only. It does not establish adaptive
migration qualification or a performance result. Raw service logs, selected
dispatch records, responses, telemetry and the comparison JSON are retained
in this directory.

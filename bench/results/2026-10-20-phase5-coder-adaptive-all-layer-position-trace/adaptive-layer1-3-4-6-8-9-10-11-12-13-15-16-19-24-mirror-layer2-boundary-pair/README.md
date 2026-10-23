# Layer-2 boundary capture after layer-24 context shift — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used seed `20261077`, the pinned
Coder IQ1_M GGUF at revision `5348543e0147355ac9cbcb031184a3546350988e`, and
candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. The
selector retained the layer-24 probe's rules but did not mirror layer 2. The
same-service 512/2,048/512 sequence generated 12 tokens per request. Both
supervised arms completed successfully.

Delayed-control initial/recovery matched all 12 token IDs, selected routes,
activations and accepted-state fingerprints. Adaptive recovery differed at
all 12 token IDs and all accepted-state/GDN hash prefixes. At every selected
position 505–511, layer-2 expert IDs and router weights matched. Expert 62
alone changed owner; its service output row differed, and the combined layer-2
MoE output differed in all 2,560 values (relative L2 `0.0005897`–`0.0038346`).
The layer-2 GDN intermediate capture first differed at `ffn_y` at all seven
positions; earlier captured fields matched. The first changed dispatch input
remained layer 3. Raw layer-2 recurrent and convolution state immediately
before and after the selected token at accepted position 511 was bit-identical
between initial and recovery. Thus this captures an owner-dependent layer-2
output delta before layer 3, while the sampled layer-2 recurrent state remains
exact; it does not establish why adaptive residency changes or the complete
state consequence.

The raw captures and derived analyses are `selected-position-analysis.json`,
`layer2-moe-analysis.json`, `layer2-gdn-analysis.json`, and
`layer2-verifier-state-analysis.json`. The MoE parts capture joins actual
service routes, expert rows and combined output. The separate native oracle
evidence for fixed-residency layer-2 ownership is in
[`service-parts-confirm3`](../../2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/service-parts-confirm3/README.md);
it covers a different fixed-residency test and is not a direct oracle join for
these seven adaptive rows.

Both 28-GiB supervisors passed with minimum host/admission availability of
14.16 GiB for adaptive-cap8 and 14.27 GiB for delayed-control, above the
six-GiB floor, and zero cgroup memory events. Clocks were observed but not
controlled; energy was not attributed. This is correctness diagnostic
evidence, not a timing or quality comparison.

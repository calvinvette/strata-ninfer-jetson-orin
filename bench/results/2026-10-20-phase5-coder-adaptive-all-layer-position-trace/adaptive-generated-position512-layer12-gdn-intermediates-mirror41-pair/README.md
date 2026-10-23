# Layer-12 GDN intermediates after the layer-41 mirror — Orin — 2026-10-20

This same-service three-request pair repeats the generated-position-512 trace
with Q8_1 selectors through layer 41. It uses Coder IQ1_M at pinned model
revision `5348543e0147355ac9cbcb031184a3546350988e`, candidate binary SHA256
`e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`, seed
`20261121`, three 512-token prompts, 12 generated tokens, and prompt cache
disabled. The capture includes layer-12 GDN intermediate fields, raw state,
MoE inputs/routes/parts/output, and all layer inputs at position 512.

Delayed control was exact. In adaptive-cap8, all captured layer-12 GDN fields
(`x`, `qkv`, `h`, `gate`, `beta`, `z`, `y`, `gdn_out`, `ffn_x`, `ffn_y`) were
bit-identical between initial, intermediate and recovery requests. The raw
layer-12 recurrent and convolution state was also identical before and after
the token in all three requests, and its post-state matched service GDN
ordinal 9. Layer-12 MoE inputs, routes, weights, expert parts, shared output
and combined output matched as well. Yet layer 13's captured input differed
between intermediate and recovery. This excludes the sampled layer-12 GDN
fields, state and MoE output, but does not establish which other residual or
hyperconnection value causes the difference.

Both supervised arms passed. Minimum host/admission availability was 14.132
GiB (adaptive) and 14.311 GiB (delayed control); there were zero cgroup memory
events. See `state-prefix-analysis.json`, each arm's
`result/gdn-intermediates-analysis.json`, and `campaign.json` for full joins
and run metadata. Raw captures and logs are retained alongside those records.
This is correctness localization, not a fix or performance result; Phase 5
remains open. The next capture should observe the residual `R`, pending write
`bo`, and inject values at the layer-12 post/layer-13 pre boundary, then the
layer-13 hyperconnection read output.

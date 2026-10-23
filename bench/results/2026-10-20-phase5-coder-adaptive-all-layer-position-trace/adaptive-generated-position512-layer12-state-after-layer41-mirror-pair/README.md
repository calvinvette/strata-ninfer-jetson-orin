# Layer-12 raw state after the layer-41 mirror — Orin — 2026-10-20

This randomized current-source pair repeats the three-request position-512
trace with the tested Q8_1 selector through layer 41. It uses the pinned Coder
IQ1_M GGUF revision `5348543e0147355ac9cbcb031184a3546350988e`, candidate binary
SHA256 `e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`,
seed `20261120`, three 512-token prompts, 12 generated tokens and
`--prompt-cache 0`. The raw verifier GDN state at layer 12 and its complete
10-expert verifier MoE parts/output were captured at position 512.

Delayed control was exact. In adaptive-cap8, the initial/intermediate
transition had identical inputs at all 48 layers at position 512. For the
intermediate/recovery transition, layer 12's MoE inputs, route IDs, router
weights, all ten expert-part outputs, shared output and combined MoE output
were bit-identical, and its raw GDN recurrent/convolution pre/post state was
also bit-identical. Each raw layer-12 post-state hash matched service GDN
ordinal 9. Nonetheless, the first changed captured activation at the next
layer was layer 13. This rules out the captured layer-12 MoE output and sampled
layer-12 raw state as the source of that layer-13 activation difference; it
leaves other layer-12 outputs or surrounding residual/normalization paths
unresolved. No GDN intermediate-field capture was enabled in this pair.

At accepted prefixes, initial/intermediate GDN hashes first differed at
prefix 2; intermediate/recovery differed at every prefix, while all token IDs
matched. This confirms the repeated-request state-history mismatch even when
the sampled layer-12 operator and raw state agree. The [layer-41 mirror report](../adaptive-generated-position512-layer41-expert171-mirror-state-pair/README.md)
contains the adjacent owner/oracle evidence.

Both arms passed the 28-GiB supervisors with minimum host/admission
availability of 14.132 GiB (delayed control) and 14.311 GiB (adaptive), with
zero cgroup memory events. Clocks remained dynamic; no performance claim is
made. `layer12-moe-analysis.json` and `state-prefix-analysis.json` are the
compact joins; raw captures and service logs remain in each arm. Phase 5
remains open. The next narrow check is to capture layer-12 GDN intermediates
and the output/residual fields feeding layer 13.

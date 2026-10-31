# Layer-5 expert 220 owner intervention

Date: 2026-10-31  
Host: Jetson AGX Orin, ARM64, CUDA/SM87  
Model/profile: Qwen3.8 Flash-Next Q2_0, same 65,536-token prompt and 32-token request  
Intervention: `STRATA_EXPERIMENT_FORCE_CPU_EXPERT=5:220:65539`

The prior matched capture found expert 220 CPU-owned in the fixed arm and
GPU-owned after adaptive swap `5:220>8` in the adaptive arm. Its inputs, route
IDs and weights were identical between those captures, and both full requests
emitted the same token IDs.

This run kept adaptive swaps enabled and forced only that GPU-resident expert
dispatch to CPU. The intervention log confirms the selected layer, expert and
position. At that dispatch, the captured input, routes and route weights matched
the existing fixed and adaptive captures exactly. Its expert outputs and
combined layer output matched the fixed CPU arm byte-for-byte. Compared with
the adaptive GPU arm, the expert-parts relative L2 was `3.86e-8`; the combined
output relative L2 was `5.77e-8`. The shared output and route data were exact.
This confirms the CPU/GPU owner effect on the sampled expert row under an exact
matched activation.

The supervised request passed in 914.9 seconds with minimum available memory
of 9,090,957,312 bytes (8.47 GiB), above the 6 GiB floor. It emitted the same
32 token IDs as the fixed and adaptive controls (SHA256
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`). Energy
was not measured. This was a state-capture intervention, not a performance
comparison.

The full 36-layer GDN checkpoint after eight generated positions differs from
the prior adaptive checkpoint at global relative L2 `0.002588` and from the
fixed checkpoint at `0.010880`. Layers 0–14 remain below relative L2 `1e-8`
versus adaptive; the first larger differences appear at layer 15 and grow in
deeper layers. At the time of the first capture there was no repeated full-state
control, so the deeper difference was not attributable.

A second forced-CPU run repeated the same prompt, dispatch, instrumentation and
generation. It returned the same token IDs, and both its captured layer-5 MoE
bundle and complete 36-layer GDN checkpoint were byte-identical to the first
forced-CPU run. Minimum available memory was 8.48 GiB on the repeat. This shows
the forced arm is repeatable for this capture, but a matched adaptive full-state
repeat under this same instrumentation is still needed to attribute the
adaptive-versus-forced deep-state difference. See
[`layer5-forced-cpu-repeatability.json`](layer5-forced-cpu-repeatability.json).

Machine-readable bundle comparisons are `layer5-forced-v-adaptive-moe.json`
and `layer5-forced-v-fixed-moe.json`. Whole-model GDN comparisons are
`layer5-forced-v-adaptive-gdn.json` and `layer5-forced-v-fixed-gdn.json`. The
captured activation, route records, supervisor logs and raw state dumps remain
in `/tmp` on the Orin host and were not added to Git.

# Exact-position CPU expert owner intervention

Date: 2026-10-31  
Host: Jetson AGX Orin, ARM64, CUDA/SM87  
Model/profile: Qwen3.8 Flash-Next Q2_0, the existing 65,536-token diagnostic profile  
Intervention: `STRATA_EXPERIMENT_FORCE_CPU_EXPERT=1:3:65540`

## Result

The opt-in hook forced layer 1 expert 3 to the normal CPU path for the single
token at absolute position 65,540. The no-accepted-prefix-trace intervention
and adaptive reference emitted the same 32 token IDs (SHA256
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`). The
captured layer-1 MoE bundle, layer-2 GDN diagnostic, layer-2 output, and committed
layer-2 state were byte-identical. The hook log confirms that the intervention
was applied. This demonstrates the local counterfactual through the next
recurrent layer for this one request and position.

A second run enabled accepted-prefix tracing and dumped all 36 layers of GDN
state after the first eight generated positions. Its state differed from the
adaptive reference globally (relative L2 `0.010784`) and from the fixed-owner
reference (`0.008204`). However, fixed-owner versus adaptive already differed
by `0.010855` under the same diagnostic setup. Layers 0–2 were bit-identical
between forced and adaptive; layers 3–4 differed only at float-roundoff scale,
and the deltas grew in deeper recurrent state. The whole-model delta is
therefore comparable to the observed same-setup run-to-run variation and does
not demonstrate a whole-model effect caused by this one owner intervention.

Both references and the intervention emitted the same token IDs. The supervised
intervention passed in 910.6 seconds with 9,190,219,776 bytes minimum available
RAM (about 8.56 GiB), above the 6 GiB guard, with no OOM. Energy was not
measured. The instrumented run's observed prompt/decode rates are not a
performance comparison and are excluded from qualification.

## Implementation and portability

The experiment hook is disabled unless its environment variable is set. It
accepts one strict `layer:expert:position` tuple, applies only to a resident GPU
owner on a one-token dispatch, and rejects a matching multi-token dispatch.
The normal CPU execution path computes the selected row. This is diagnostic
code, not a production owner policy.

The CUDA `strata` target built on Orin with one job and exercised the hook in the
supervised request. The shared source also built with one job on maestro1 for
HIP and SYCL. HIP `strata --help` exited 0 (SHA256
`c48cb93ff79b75b6740ae21ea51b440a241e890a66334232bc92f88053d08902`). SYCL
compiled and linked (SHA256
`dad18286e8a2a3a6fc278817b26623e17137f629a4a2dff91ca23aeb6aefa85e`). Its help invocation
aborted because maestro1 has no SYCL device. These x86 builds do not establish
HIP or SYCL device execution.

Machine-readable state comparisons are in `forced-v-adaptive-gdn.json`,
`forced-v-fixed-gdn.json`, and `fixed-v-adaptive-gdn.json`. Source captures and
supervisor logs remain in `/tmp/e6-owner3-causal-*` on the test hosts and were
not copied into Git.

A second intervention at the earlier sampled owner transition is documented
in [layer5-expert220-intervention.md](layer5-expert220-intervention.md), with
its own local MoE and full-state comparisons.

## Interpretation and next step

This closes the single-position local owner-intervention question, not E6 or
E7. The one-position intervention reproduces the adaptive local layer-1 and
layer-2 captured state in the minimally instrumented run, while the whole-model
checkpoint remains within the scale of same-setup repeat variation. Next
investigate repeatability at deeper state checkpoints and use a less intrusive
full-state capture or multiple matched controls before claiming a long-range
causal effect. No speedup, quality, or generalization claim follows.

# Layer-13 expert 474 owner intervention

Date: 2026-10-31  
Host: Jetson AGX Orin, ARM64, CUDA/SM87  
Model/profile: Qwen3.8 Flash-Next Q2_0, same 65,536-token prompt and 32-token request  
Intervention: `STRATA_EXPERIMENT_FORCE_CPU_EXPERT=13:474:65540`

The prior matched owner capture found expert 474 GPU-resident in the adaptive
arm at position 65,540, after promotion `13:474>1`. Its adaptive input, route
IDs and weights are now compared with a run that changed only that row's owner
to CPU. The input, IDs and route weights are bit-identical. The forced CPU
expert-parts row differs from the adaptive GPU row by relative L2 `3.56e-8`;
the combined layer output differs by `6.44e-8`. The intervention log confirms
the exact dispatch.

Both forced-CPU runs passed and returned the same 32 token IDs as adaptive
(SHA256
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`). Their
captured MoE bundle and complete 36-layer GDN checkpoint after eight generated
positions are byte-identical. An adaptive checkpoint from the matched full
state control exactly matches its earlier adaptive repeat. Minimum available
memory was 8.40 GiB and 8.44 GiB in the forced runs, above the 6 GiB floor;
sampled cgroup OOM kills were zero. Energy was not measured.

Compared with the repeatable adaptive checkpoint, forced CPU first differs
materially at GDN layer 18; global relative L2 across the checkpoint is
`0.008878`. Exact same-arm repeats and the matched input/route capture support
a causal link from this one owner change to the later GDN state difference for
this request. This is bounded state evidence. It does not establish a quality
impact, performance improvement, or explain other request/state drift. The
instrumented request timing is not a performance measurement.

Machine-readable comparisons are `layer13-forced-v-adaptive-moe.json` and
`layer13-forced-v-adaptive-gdn.json`; run identities and hashes are in
`layer13-forced-cpu-repeatability.json`. Raw captures and supervisor logs remain
in `/tmp` on Orin and were not copied into Git.

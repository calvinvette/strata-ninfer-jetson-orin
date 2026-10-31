# Layer-7 expert 225 owner intervention

Date: 2026-10-31  
Host: Jetson AGX Orin, ARM64, CUDA/SM87  
Model/profile: Qwen3.8 Flash-Next Q2_0, same 65,536-token prompt and 32-token request  
Intervention: `STRATA_EXPERIMENT_FORCE_CPU_EXPERT=7:225:65539`

The matched adaptive owner capture records expert 225 as GPU-resident at
position 65,539 after promotion `7:225>1`. In the forced-CPU run, the selected
MoE activation, route IDs and route weights matched the adaptive run exactly.
The expert-parts row changed by relative L2 `2.93e-8`; the combined layer
output changed by `4.30e-8`, while shared output, routes and weights were exact.
This isolates the numeric effect of the owner for the sampled dispatch.

Two forced-CPU runs passed and returned the same 32 token IDs as the adaptive
control (SHA256
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`). Their
captured layer-7 MoE bundle and complete 36-layer GDN checkpoint after eight
generated positions were byte-identical. Minimum available memory was 8.47 GiB
and 8.45 GiB; sampled cgroup OOM kills were zero. The adaptive checkpoint
matched its independently repeated adaptive control byte-for-byte.

The forced-versus-adaptive GDN checkpoint first exceeds relative L2 `1e-8` at
layer 16 (`7.96e-7`), rises to `0.00182` at layer 17, and has global relative
L2 `0.008355`. The exact same-arm repeats and unchanged input/routing establish
a bounded causal GDN state effect from forcing this CPU/GPU owner for this
request, despite the small local expert-row delta. This is not a quality or
performance result and does not explain other state drift. Energy was not
measured.

Machine-readable comparisons are `layer7-forced-v-adaptive-moe.json` and
`layer7-forced-v-adaptive-gdn.json`; repeat identities and hashes are in
`layer7-forced-cpu-repeatability.json`. Raw captures and supervisor logs remain
in `/tmp` on Orin and were not copied into Git.

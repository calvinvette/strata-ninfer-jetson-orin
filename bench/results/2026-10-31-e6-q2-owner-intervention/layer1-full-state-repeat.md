# Layer-1 forced-owner full-state repeat

Date: 2026-10-31  
Host: Jetson AGX Orin, ARM64, CUDA/SM87  
Model/profile: Qwen3.8 Flash-Next Q2_0, 65,536-token prompt + 32 generated tokens  
Intervention: `STRATA_EXPERIMENT_FORCE_CPU_EXPERT=1:3:65540`

## Repeat result

A second fresh-process forced-CPU intervention used the same captured prompt,
profile, 3,000-entry cache, 6 GiB resident budget, 3 GiB workspace reserve,
128-token prefill, eight workers, MTP-2, and disabled prompt cache and PCIe
staging as the original capture. It emitted all 32 same token IDs, SHA256
`2d5f3da8f9890f8c9262231bada2cfab088196528565a1c08ab685d86074c650`.
The run passed the supervisor with minimum available RAM of 9,337,884,672 bytes
(8.70 GiB), above the six-GiB floor, and zero sampled cgroup OOM kills. Timing
is diagnostic; energy and read-only clocks were not collected.

The full 36-layer GDN checkpoint does not repeat byte-for-byte. Relative L2
between the original and repeated forced-CPU arms is `0.0107827`, with
87.42% of values different. Layers 0–2 are exact; layer 3 differs only at
relative L2 `5.43e-10`, and layer 4 at `7.60e-10`. The delta reaches `0.001339`
at layer 5 and `0.005118` at layer 6. The original forced-CPU versus adaptive
comparison was also `0.010784` globally. Thus the full-state variation within
the forced-CPU arm is approximately the same magnitude as the earlier
cross-arm comparison.

Both the local MoE/layer-2 counterfactual and token sequence remain useful for
this request: the intervention still demonstrates byte-identical layer-1/2
captures in the minimally instrumented run, and the two full-state runs return
the same tokens. The repeated full-state data do **not** support attributing the
later whole-model difference to this single layer-1 intervention. Layer-1
long-range causal attribution remains unresolved; retain only the bounded local
result. This does not invalidate the independently repeated layer-5, layer-7
or layer-13 interventions.

The machine-readable comparison is
[`layer1-forced-repeat-gdn.json`](layer1-forced-repeat-gdn.json). Both raw
state dumps and the API run logs remain under `/tmp/e6-owner3-causal-*` and
were not copied into Git.

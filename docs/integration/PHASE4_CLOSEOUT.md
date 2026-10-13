# Phase 4 closeout — tested Orin kernel candidates — 2026-10-14

Phase 4 is complete for the measured Orin AGX kernel and ARM CPU candidates.
This closes the plan's profiling, contract, selected dispatch, end-to-end
confirmation and affected-backend build gates for these candidates. It does not
claim a generally optimal serving profile, broad task quality, energy savings,
or sustained-service benefit. No performance default changed.

| Candidate / gate | Evidence and decision |
| --- | --- |
| Q6_K to FP16 dequantization | The request profile identified this as the largest named kernel. The opt-in warp-per-group layout is bit-identical to production over 76,349,440 outputs across five real IQ1_M matrix shapes and three independent processes. Independent real-payload FP16 checks cover 51,200 values. The source hash in the record matches the current `src/kernels/cuda/dequant_bf16.cu`. CTA alternatives had no consistent win and were rejected. |
| Q6_K end-to-end behavior | Randomized seven-pair Orin confirmations cover 512/64 and 2,048/128 requests, 8K/16K/32K configured contexts, fixed MTP comparisons, and an accepted-only MTP × warp design. The accepted-only seven-block run matched outputs across warp off/on and MTP off/window4; request medians improved 7.279% and 6.355% respectively, with paired 95% intervals excluding zero. A traced pair matched accepted-prefix state. These results qualify only the recorded model, prompt shapes, cache and adaptation policy. Warp dispatch stays opt-in as `STRATA_Q6K_WARP_DEQUANT=1`. |
| Q8_1 NEON quantization | The Strata-specific quantization contract (half-away-from-zero, scale, codes, integer sum and correction) matched exactly in the independent oracle and production dispatch tests. Seven randomized operator pairs measured a 29.666% median quantizer reduction (95% paired interval −29.845% to −29.432%). The three-pair 512/8 Q2_0 serving screen was effectively tied (+0.019% total request, with prompt time 0.444% slower), so the scalar dispatch remains default and NEON remains opt-in. The full HIP and SYCL builds and final relinks are recorded; these are x86 build checks, not accelerator runtime evidence. |
| ARM worker contribution | Worker screens include a correctness-gated traced 1/2/4/8 comparison and no-trace request screens at 512 and 1,069 tokens. Eight workers won the tested cells, but confirmation effects were small and scoped to specific prompts, cache and CPU-prefill policy; the 11-worker arm failed correctness. No worker default or general worker profile is promoted. |
| Fresh focused regression | On 2026-10-14, `q8_1_scalar_contract_test`, `q8_1_neon_contract_test` and `expert_multi_test` passed 3/3 in the current Orin candidate build under a 28-GiB cgroup scope and the six-GiB host-availability guard. Minimum host availability was 26,341,785,600 bytes. The result is retained at `bench/results/2026-10-14-phase4-closeout/ctest/supervisor/`. |

The current opt-in Q6 result is an isolated kernel-path qualification. Phase 5's
adaptive-swap/MTP accepted-state failure remains open and prevents qualification
of a combined default profile. Phase 6 must still evaluate supported
interactions and produce a Pareto decision; Phase 7 must establish task quality,
capacity and sustained service behavior. Runtime CUDA evidence is from Orin;
maestro1 HIP/SYCL evidence is compile/link only. Nsight Compute counters,
energy attribution and broad task-quality evaluation remain unavailable or
untested. Reopen Phase 4 if a kernel or dispatch contract changes, or if a new
model/backend enters scope.

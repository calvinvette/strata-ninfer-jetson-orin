# Long-chain owner transition at layer 21 / position 515 — Orin — 2026-10-22

This current-binary Coder IQ1_M run captured all-layer expert ownership at
position 515 across the held-out short–short–short sequence, with 256 generated
tokens per request, adaptive cap 8 and `STRATA_NATIVE_CPU_Q8_1_DOT=all`. The
model/workload identity and token sequence match the separate raw layer-22
state capture. The run passed its 28-GiB supervisor in 766.67 seconds; minimum
host/admission availability was 14.22 GiB and sampled cgroup
low/high/max/OOM/OOM-kill events were zero. Clocks were dynamic, EMC readback
was denied and energy was not attributed.

Across initial, intermediate and recovery requests, layer-21 position-515
token ID, expert IDs, router weights and the 2,560-value MoE input are
bit-identical. Expert 132 at rank 9 changes owner from CPU to GPU between the
initial and intermediate requests; the recovery keeps the GPU owner. Its
verifier row changes in all 2,560 values (relative L2 `0.016716`), changing the
combined MoE output in 2,559/2,560 values (relative L2 `0.001528`). The
recovery row and combined output then match the intermediate request exactly.

The captured layer-21 input SHA256 is
`4d7bae5e8f1a2d247f4d726f40557f238fb34fcc9bceff44349e4e215fe6de2f`, exactly
the input used by the earlier [independent native-expert oracle](../2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/operator-oracle-open-response/layer21-expert132/README.md).
The current initial CPU row and intermediate/recovery GPU rows are bit-identical
to the corresponding earlier service rows for this activation; that oracle
matched each owner-specific service row bit-for-bit. The owner-dependent
numerical effect is therefore repeated at the same input in this longer
short–short–short history.

Layer 22 is the first downstream point in this capture where the MoE input
changes: relative L2 is `9.46e-4` initial→intermediate, `1.67e-4`
intermediate→recovery, and `9.40e-4` initial→recovery. The raw committed
layer-22 state at position 515 changes by relative L2 `2.60e-4` in recurrent
state and `7.00e-4` in convolution history initial→intermediate; it changes
again by `4.89e-5` and `3.59e-4` intermediate→recovery. The delayed control's
raw state was bit-exact at positions 515, 530 and 640. This confirms expert 132
ownership as one numerical contributor and places downstream state changes
after it, while also showing that other owner/history changes contribute to
the intermediate→recovery state shift. It does not establish a complete causal
account or a general recovery tolerance.

The 16-token [position-515 control](../2026-10-22-phase5-coder-position515-owner-followup-16/README.md)
had no layer-21 owner change and no state divergence, so the transition depends
on the longer adaptive history in this workload. The long-chain raw-state
captures and their incomplete endpoint requests are described in the
[raw-state report](../2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md).

`analyze_owner_transition.py` regenerates `analysis.json`, checks all 48 layers
and all three requests, verifies the repeated token path, compares layer-21
expert rows and combined outputs, joins layer-22 raw state, and cross-checks
the raw GDN hashes against service ordinal 17. `SHA256SUMS.txt` pins the report,
analyzer, request IDs, dispatch capture, service log and supervisor result.
Captured data and telemetry are retained here. No model or build product is
stored in the repository.

# Layer-30 selected expert and layer-32 state capture

This diagnostic pair used the Coder `IQ1_M` model from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, with prompt caching
disabled. It enabled CPU Q8_1 dot overrides at layers 8, 13, 16, 24, 28 and 29,
then captured the layer-30 MoE, selected CPU expert outputs, and layer-32 GDN
state at prompt position 511. The delayed-control arm kept adaptation delayed.
Both supervised runs passed; minimum available host/admission memory was 14.096
GiB for adaptive and 14.297 GiB for delayed control. Adaptive recovery differed
from its initial request at 6/12 generated token IDs; delayed control matched.

At layer 30, experts 121 and 212 changed owner from CPU to GPU between the
adaptive initial and recovery service traces while the captured routing IDs,
router weights and activation inputs matched. The independently captured CPU
pool rows for these experts match the `native_expert_parity` CPU outputs
bit-for-bit (2,560 values each). For this exact captured activation, the
parity tool's CPU and GPU outputs are also bit-identical. The comparison is
recorded in `adaptive-cap8/result/operator-oracles/operator-comparison.json`.

The verifier's three captured per-expert rows are the mixed-owner parts used by
its MoE combine, separate from the direct CPU-pool JSONL capture. The oracle GPU
outputs match verifier rows 1 and 2, but not row 3. Although the service trace
contains matching layer-30 activation records for its first and recovery
requests, the exact verifier input activation was not captured. Therefore the
request-3 mismatch cannot be attributed to arithmetic or to the selected
experts; input equivalence is unproven. This cell is unresolved and is not
counted as a same-input parity pass.

The layer-32 prompt-prefill state is bit-identical across the three no-cache
requests. At generated position 511, raw layer-32 state remained exact from
initial to intermediate; from intermediate to recovery, pre-state matched and
post-state differed in 786,423/786,432 recurrent values and 10,240/30,720
convolution values. The per-GDN accepted-prefix mismatch starts at model layer
34 for initial-to-intermediate and layer 12 for intermediate-to-recovery.
Initial-to-recovery's first captured activation difference is at layer 34.
This confirms that the selected layer-30 CPU/GPU outputs do not explain the
later history-dependent state result in this capture; it does not locate the
first causal state-changing operation. Phase 5 remains open.

Reproduction inputs and raw captures are in `adaptive-cap8/` and
`delayed-control/`; model files remain outside Git under `~/models/`.

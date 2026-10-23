# IQ3_S/Q2_0 layer-21 parity intervention

This paired Orin diagnostic asked whether the CPU/GPU arithmetic difference for
layer-21 expert 132 explained the long-chain adaptive recovery mismatch. It does
not. The selector is opt-in and scoped to the pair and layer:
`STRATA_NATIVE_CPU_Q8_1_DOT=iq3_s/q2_0@layer=21`.

The held-out Coder workload was three sequential 512-token prompts, each
requesting 256 generated tokens (`short-short-short`, seed `20261022123`). Both
arms used the same service, model, binary, prompt cohort, and dynamic clock
policy. The treatment used adaptive cap-8 placement; the control delayed
adaptation. The model is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. Binary SHA256:
`afc710def2ad1c0f0905afa015f5cae3e50063b29d7c4fdd62f186ab21a7358d`.

Independent real-weight checks on the exact captured layer-21 inputs found the
selected CPU and CUDA expert outputs bit-identical (0/7,680 differing output
words) for both initial and intermediate requests. The default CPU path differed
from CUDA on the earlier initial activation (relative L2 `0.0166`, all 7,680
words different). This qualifies this operator/input pair; it does not establish
end-to-end correctness or performance.

In the end-to-end pair, adaptive recovery differed from its initial request on
254/256 output tokens and changed accepted-state fingerprints for GDN, PLE,
tail, pooled, pooled-full, KV and previous PLE. The delayed-control arm had zero
token differences and unchanged fingerprints. At layer 21, position 515, the
first two adaptive requests still had the same token (`16661`) and top-10 expert
IDs (`239,55,54,74,85,104,21,132,252,236`), but their routing weights differed
(top weight `0.206266537` vs `0.207088962`). The recovery request had already
changed token and route. The captured layer-21 input vectors for those first two
adaptive requests already differed in all 2,560 values (relative L2 `0.02186`,
maximum absolute difference `0.05446`). Their committed layer-22 states at
position 515 differed in 817,149/817,152 values (relative L2 `0.0140722`); the
three delayed-control states were bit-identical at captured positions 515, 530
and 640. Different later tokens make later adaptive states non-comparable as a
causal test.

Both supervised runs passed with the required 6 GiB host-availability floor,
28 GiB cgroup cap and no cgroup OOM events. The adaptive run took 740.69 s and
retained a 13.78 GiB minimum physical/admission availability; delayed control
took about 739.5 s with 14.03 GiB minimum. Instrumentation and the small number
of pairs do not support a performance conclusion. Energy was not measured.

Conclusion: equalizing the selected CPU/GPU expert arithmetic does not remove
the adaptive recovery mismatch. The layer-21 activation, router weights and
same-token committed state already differ, so the selected expert output is
downstream of an existing divergence. This does not identify where that earlier
divergence begins. Phase 5 remains open; this result is a narrowed negative
root-cause test, not a resolution. Raw traces, binary captures and local oracle
output stay in the local experiment directory and are not committed.

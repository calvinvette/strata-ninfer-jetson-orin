# Layer-11 adaptive owner transition and expert-201 output at position 515

This Coder IQ1_M short/long/short pair follows the changed layer-11 `bo`
boundary found in the adjacent campaign. Seed: `2026102234`. Binary SHA256:
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`; source
tree HEAD `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`. The artifact is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M, revision
`5348543e0147355ac9cbcb031184a3546350988e`. Both supervised service arms
passed. They emitted identical short-request tokens; delayed-control accepted
state recovered bitwise, while adaptive accepted fingerprints changed.

At position 515, adaptive recovery preserves layer-11 input, expert IDs and
router weights, but changes ownership for ranks 8 and 9: expert 201 and expert
63 move from CPU to GPU. Delayed control keeps both on CPU. The layer-11 QSA
activation is bit-identical across adaptive initial/recovery. In the verifier
parts, expert 201 is the only expert row that changes: all 2,560 output values
differ, with relative L2 `4.41508e-4`. Expert 63's output is bit-identical
across its ownership change. The combined pre-residual MoE output changes in
all 2,560 values; delayed control's routes, weights, all expert rows and
combined output remain bit-identical.

Expert 201 uses the IQ2_S/IQ4_NL weight pair. An independent
`native_expert_parity` run used its same captured activation and model weights,
with `STRATA_NATIVE_CPU_Q8_1_DOT=all`. The
service's initial CPU row matched the independent CPU result bitwise; the
recovery GPU row matched the independent GPU result bitwise. The independent
CPU/GPU outputs differed in all 2,560 values, relative L2 `4.395e-4`, closely
matching the service migration delta. The same-input oracle therefore
attributes the observed layer-11 expert-output change to the CPU/GPU execution
path for expert 201 under this Q8_1 selector. The layer-11 boundary report
shows `bo` then differs, followed by a changed layer-12 GDN update. This is a
specific operator seam and causal chain for one captured token; it does not
bound accepted-state drift over other prompts or qualify the adaptive policy.

Minimum host/admission availability was 14.27 GiB for delayed control and
14.33 GiB for adaptive, with zero cgroup memory events. The first oracle
invocation failed before running the operator checks because its output
directory was absent and it supplied a layer flag unsupported by the utility;
that failed setup is retained under `operator-checks/.../supervisor/`. The
corrected invocation used a created output directory and positional layer 11,
and passed under the 28-GiB supervisor. See `adaptive-layer11-moe.json`,
`delayed-layer11-moe.json`, the adjacent `dispatch-analysis.json`, and the
operator-oracle comparison and raw outputs under
`operator-checks/layer11-position515/expert201/`.

Reproduction of the paired service capture:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 2026102234 --continuations 0 --sequence short-long-short \
  --generated-tokens 12 --native-cpu-q8-1-dot all \
  --capture-moe-positions 515 --capture-moe-rows 96 \
  --capture-verify-moe-layer 11 --verify-moe-positions 515 \
  --verify-moe-input-layers same \
  --capture-boundary-layer 11 --boundary-position 515 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-source-layer11-owner-output-position515
```

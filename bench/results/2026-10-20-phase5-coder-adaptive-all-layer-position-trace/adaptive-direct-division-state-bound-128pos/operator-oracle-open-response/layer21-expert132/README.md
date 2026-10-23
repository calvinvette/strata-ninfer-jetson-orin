# Independent oracle for the open-response layer-21 expert migration

This checks the same expert-132 activation against Strata's independent native CPU and CUDA expert implementations. The activation is from Coder IQ1_M, model revision `5348543e0147355ac9cbcb031184a3546350988e`, at layer 21/position 515; its 2,560 float32 values have SHA256 `4d7bae5e8f1a2d247f4d726f40557f238fb34fcc9bceff44349e4e215fe6de2f`. Initial and recovery capture inputs are bit-identical. The rank-9 expert weight pair is IQ3_S/Q2_0.

`native_expert_parity` passed with `STRATA_NATIVE_CPU_Q8_1_DOT=all`. The captured initial CPU service row matches the same-input CPU oracle bit-for-bit; the recovery GPU row matches the same-input GPU oracle bit-for-bit. The independent CPU and GPU outputs differ in all 2,560 values (relative L2 `0.016716`). This matches the captured owner-dependent row change in both the selector and no-selector campaigns. Their combined layer-21 output change is relative L2 `0.001528`; the first changed full MoE input is layer 22 (relative L2 `0.0009572`). Delayed controls retain CPU ownership and exact layer-21 rows/output.

The same service capture and activation were reused for both configuration comparisons. The oracle binary SHA256 is `54da46c53cee72303061704fd073fc07b494749c0c2a8b1a779e7937d428a735`; its run passed in 1.07 s with 24.42 GiB minimum host/admission availability. Frequencies were read only; EMC frequency was inaccessible and energy was not measured. This oracle establishes the numerical owner difference for this one activation, not the general adaptive policy or a performance result.

Reproduction:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/operator-oracle-open-response/layer21-expert132/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  /usr/bin/env STRATA_NATIVE_CPU_Q8_1_DOT=all \
  build/integration/candidate/native_expert_parity \
  /home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert 132 \
  --activation-f32 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/operator-oracle-open-response/layer21-expert132/activation.f32 \
  --dump-f32-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/operator-oracle-open-response/layer21-expert132/oracle \
  21
```

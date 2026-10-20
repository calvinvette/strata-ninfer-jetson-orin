# Layer-31 expert-22 Q8_1 stage isolation — Orin — 2026-10-20

This re-ran `native_expert_parity` on the captured layer-31 position-519
activation from the pinned Coder IQ1_M snapshot. The candidate binary hash is
`14afd1a4b953e176a88d7812bddcdf2beb65944bb5795beaf0f37e5834a496aa`; the
harness hash and activation hash are in `stage-isolation.json`.

The CPU and CUDA activation Q8_1 byte streams matched exactly. After the
expert's gate/up and SwiGLU computation, 3 of 60 hidden Q8_1 blocks differed,
only in the FP16 `d` scale: CPU `0x1a78`, CUDA `0x1a79`. The block sums and all
32 integer codes per block were identical. Applying the CPU IQ4_NL down
projection to the CUDA-produced hidden Q8_1 blocks reproduced the grouped CUDA
output bit-for-bit (0/7,680 float words differed). The ordinary CPU and CUDA
expert outputs differed in 2,559/2,560 values (relative L2 `1.31992e-4`).

This localizes the mismatch to gate/up output before hidden quantization. The
CUDA kernel uses fast exp/division/SwiGLU operations; that is a candidate source,
not yet an isolated cause. The harness's auxiliary float-stage buffers do not
represent valid writes from this fused gate/up kernel and are excluded. The
saved Q8_1 records and complete harness output are the evidence used here.

Reproduce on the Orin checkout from repository root:

```sh
STRATA_NATIVE_CPU_Q8_1_DOT=iq3_xxs/iq4_nl@layer=31 \
STRATA_PARITY_COMPARE_HIDDEN_Q8_1=1 \
STRATA_PARITY_DUMP_HIDDEN_Q8_1=1 \
build/integration/candidate/native_expert_parity \
  "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --expert 22 \
  --activation-f32 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/operator-checks/layer31-position519/activation.f32 \
  --dump-f32-dir /tmp/strata-expert22-stage 31
```

The paired service records, model provenance and accepted-state cross-check are
in the parent [adaptive recovery capture](../../adaptive-state-prefix8-verifier-capture/README.md).
This diagnostic provides no performance or task-quality result; Phase 5 stays
open.

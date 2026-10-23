# Layer-31 expert-22 Q8_1 stage isolation — Orin — 2026-10-20

This re-ran `native_expert_parity` on the captured layer-31 position-519
activation from the pinned Coder IQ1_M snapshot. The candidate binary hash is
`14afd1a4b953e176a88d7812bddcdf2beb65944bb5795beaf0f37e5834a496aa`; the
harness hash and activation hash are in `stage-isolation.json`.

The CPU and CUDA input Q8_1 byte streams matched exactly. With the explicit
CUDA mode-0 path, an independent scalar IQ3_XXS/Q8_1 dot matched all 1,920 gate
and 1,920 up values bit-for-bit against CUDA's captured stages. After SwiGLU,
3 of 60 hidden Q8_1 blocks differed only in the FP16 `d` scale: CPU `0x1a78`,
CUDA `0x1a79`. The block sums and all 32 integer codes per block were identical.
The default Orin mode produced the same CUDA hidden Q8_1 bytes as explicit mode
0. Applying the CPU IQ4_NL down projection to those CUDA-produced hidden blocks
reproduced grouped CUDA output bit-for-bit (0/7,680 float words differed). The
ordinary CPU and CUDA expert outputs differed in 2,559/2,560 values (relative
L2 `1.31992e-4`).

This rules out the gate/up dot and down projection for this captured input and
localizes the numeric difference to SwiGLU output or its hidden quantization
scale. CUDA's fast exp/divide/multiply path is a plausible source, but the exact
operation has not yet been isolated. The mode-0 gate/up arrays are valid stage
captures; no unstored float intermediate is used in the conclusion.

Reproduce on the Orin checkout from repository root:

```sh
STRATA_EXP_MODE=0 \
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

The original 3/60 hidden-block scale difference above was reproduced with the
division-form CPU SiLU. A follow-up changed the opt-in CPU operation order to
the reciprocal sigmoid form and made the captured CPU/CUDA expert output,
hidden Q8_1 blocks and down projection bit-identical; see the separate
[reciprocal-SiLU parity record](reciprocal-silu-parity/README.md). The paired
service test still found adaptive committed-state divergence at position 518,
so the operator improvement does not resolve migration recovery.

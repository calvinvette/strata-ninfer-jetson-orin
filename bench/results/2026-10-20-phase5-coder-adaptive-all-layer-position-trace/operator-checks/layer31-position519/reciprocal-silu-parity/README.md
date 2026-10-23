# Reciprocal-SiLU CPU/CUDA parity — Orin — 2026-10-20

This repeats the layer-31, expert-22 same-input oracle after changing the
opt-in CPU Q8_1 expert path to use `sigmoid = 1 / (1 + exp(-g))` and
`hidden = (g * sigmoid) * up`. It uses the captured position-519 activation
from the pinned Coder IQ1_M model. The independent harness binary SHA256 is
`015744e138d311d09927eb9386a9c77424ce1f0eebf054d6628dd4716aab69b6`; the
activation SHA256 is
`bf609469743a057a07de8b514bf616399e84fe79fc84f71ca643cfe9f950e824`.

With `STRATA_EXP_MODE=0` and selector
`iq3_xxs/iq4_nl@layer=31`, input Q8_1 bytes, 1,920 gate dots, 1,920 up dots,
all 60 hidden Q8_1 blocks and all 7,680 expert output words matched bitwise.
The independent packed-weight reconstruction also matched the CPU hidden
values. `output.txt` retains the exact command's harness output; the small
stage dumps retain the values needed to inspect the equal Q8_1 inputs, gate/up
stages and hidden blocks. Large dequantized weight dumps were omitted because
the GGUF is the source of truth.

Reproduce from repository root:

```sh
STRATA_EXP_MODE=0 \
STRATA_NATIVE_CPU_Q8_1_DOT=iq3_xxs/iq4_nl@layer=31 \
STRATA_PARITY_COMPARE_HIDDEN_Q8_1=1 \
STRATA_PARITY_DUMP_HIDDEN_Q8_1=1 \
build/integration/candidate/native_expert_parity \
  "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --expert 22 \
  --activation-f32 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/operator-checks/layer31-position519/activation.f32 \
  --dump-f32-dir /tmp/strata-parity-layer31-final 31
```

This is an operator result for one captured input. The delayed/adaptive service
pairs show that it does not establish accepted-state recovery; see the
[layer-31-only service result](../../../adaptive-prefix8-layer31-silu-check/README.md).

# Direct-division SwiGLU replay — layer 3 expert 182 — Orin — 2026-10-20

This isolated replay applied the direct-division expression tested on the
layer-39 expert-90 row to the captured layer-3 expert-182 activation. Both use
IQ2_S/IQ4_NL with CUDA-order Q8_1 gate/up inputs. The temporary source change
is retained in [`direct-silu-operation-order.patch`](direct-silu-operation-order.patch);
the production source was restored after the replay and again passes its
focused operator tests.

For layer 3, the direct-division hidden floats differ from the reciprocal-form
reconstruction at 408/1,920 entries (maximum absolute delta `7.45e-9`,
relative L2 `4.04e-8`), but the Q8_1 bytes do not change: CPU and CUDA hidden
blocks match exactly (0/60 differing), and CPU and CUDA expert outputs are
bit-identical (0/7,680 differing). The existing reciprocal
baseline for this same activation also has identical packed hidden bytes and
expert outputs. Thus direct division does not improve the encoded result on
this row. The parity executable returned status 1 because its independent
float reconstruction still requires the reciprocal expression; the direct
GPU-stage comparison, packed hidden comparison, down-projection comparison,
and final CPU/GPU output comparisons all passed. This makes the run a
diagnostic result rather than a passing parity test.

Together with the layer-39 result, this shows that changing the operation
order can alter three sensitive hidden-block scales for one activation while
leaving another activation's packed result unchanged. The layer-31 IQ3_XXS
case also regressed under the same global division change. This does not
support a general or format-wide formula change; no source change remains.
See the [layer-39 trial](../../../../adaptive-generated-position521-layer39-moe-q8-pair/silu-order-trial.md)
and [layer-31 reciprocal contract](../../../../operator-checks/layer31-position519/README.md).

Reproduce after applying the retained patch and rebuilding
`native_expert_parity`:

```sh
git apply bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer3-generated-position520/operator-checks/expert182-q8_1-mirror/direct-silu-division/direct-silu-operation-order.patch
cmake --build build/integration/candidate --target native_expert_parity --parallel 2
mkdir -p /tmp/expert182-direct-silu
STRATA_EXP_MODE=0 \
STRATA_NATIVE_CPU_Q8_1_DOT=iq2_s/iq4_nl@layer=3 \
STRATA_PARITY_COMPARE_HIDDEN_Q8_1=1 \
STRATA_PARITY_DUMP_HIDDEN_Q8_1=1 \
build/integration/candidate/native_expert_parity \
  "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --expert 182 \
  --activation-f32 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer3-generated-position520/operator-checks/expert182-q8_1-mirror/activation.f32 \
  --dump-f32-dir /tmp/expert182-direct-silu 3
git apply --reverse bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer3-generated-position520/operator-checks/expert182-q8_1-mirror/direct-silu-division/direct-silu-operation-order.patch
```

The archived raw CPU/GPU outputs, packed hidden rows and text result are
compared by:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer3-generated-position520/operator-checks/expert182-q8_1-mirror/direct-silu-division/compare_silu_operation_order.py
```

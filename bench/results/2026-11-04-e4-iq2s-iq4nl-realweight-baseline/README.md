# Mixed-codec real-weight baseline: IQ2_S / IQ4_NL

Date: 2026-11-04. Hardware: Jetson Orin AGX, CUDA build from the active
`feat/ninfer-expert-e0` worktree.

This run qualifies the first common mixed-codec tuple identified in both Coder
IQ1_M and ISTA-DASLab IQ3_S inventories. A header-only inventory of the full
Coder IQ1_M shards selected layer 2 as the first IQ2_S gate/up, IQ4_NL down
layer; the tuple appears at layers 2, 3, 4, 5, 6, 9, 11, 15, 19, 23, 24, 26,
32, 34 and 39. The corresponding inventory files remain outside Git. Model
payloads remain under `~/models/`.

The existing `native_expert_parity` harness first ran against actual layer-2
expert 0 weights. It reported a 1,971,200-byte expert blob, passed its CPU/GPU
parity check, and verified GPU dequantization against GGML `to_float`: zero
differing bits across 4,915,200 values; 0/640 embedding values differed.
CPU/GPU output relative difference was 1.49% on its generated activation.

The stronger fixture uses the retained service activation for layer 2, position
511, token 271, paired with routed expert 174. Its SHA256 is
`863084edc13c3a66e8b6827d0df22bbe1fb18917617fa61d1e026665f628acec`. The same
real-weight harness passed with zero failures: CPU relative-L1 to its FP64
reference was 1.22%, GPU was 1.04%, and CPU/GPU outputs differed by 1.56%
(7,680/7,680 float values). The FP64 reference uses GGML's `to_float`
dequantizer followed by independent FP64 projection arithmetic; codec decode
is not independent of GGML. The raw captured activation remains in its
existing evidence directory and was not copied.

This is a pre-integration Strata baseline and fixture qualification. It does
not exercise any NInfer-derived IQ2_S/IQ4_NL code, prove whole-model support,
or establish a performance benefit. The random harness input is not a captured
model activation. A follow-up adapter test must use real weights and a pinned
activation, an independent mathematical/codec oracle, and explicit dispatch
evidence.

## Reproduction

```sh
python3 tools/integration/inventory_tensors.py \
  --shard ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --shard ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf \
  --output /tmp/coder-iq1m-inventory.json
build/integration/e0-cuda-build/native_expert_parity \
  ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert 0 2
build/integration/e0-cuda-build/native_expert_parity \
  ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert 174 --activation-f32 \
  bench/results/2026-10-19-phase5-coder-layer2-operator-oracle/activation-position-511-token-271-layer-2.f32 2
```

The source revision, executable hash, and two shard hashes are recorded beside
this report. Raw model weights and activation payloads are not copied into the
repository.

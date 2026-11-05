# Mixed-codec real-weight baseline: IQ2_S / IQ4_NL

Date: 2026-11-04. Hardware: Jetson Orin AGX, CUDA build from the active
`feat/ninfer-expert-e0` worktree.

This run qualifies the first common mixed-codec tuple identified in both Coder
IQ1_M and ISTA-DASLab IQ3_S inventories. A header-only inventory of the full
Coder IQ1_M shards selected layer 2 as the first IQ2_S gate/up, IQ4_NL down
layer; the tuple appears at layers 2, 3, 4, 5, 6, 9, 11, 15, 19, 23, 24, 26,
32, 34 and 39. The corresponding inventory files remain outside Git. Model
payloads remain under `~/models/`.

The existing `native_expert_parity` harness ran against actual layer-2 expert
0 weights. It reported a 1,971,200-byte expert blob, passed its CPU/GPU parity
check, and verified GPU dequantization against GGML `to_float`: zero differing
bits across 4,915,200 values; 0/640 embedding values differed. CPU/GPU output
relative difference was 1.49%, as expected for their distinct activation
quantization paths. The process ended with `native_expert_parity: 0 failures`.

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
```

The source revision, executable hash, and two shard hashes are recorded beside
this report. Raw model weights and activation payloads are not copied into the
repository.

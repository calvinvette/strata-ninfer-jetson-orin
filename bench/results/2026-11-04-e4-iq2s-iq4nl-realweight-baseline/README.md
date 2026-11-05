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

## IQ2_S byte decoder qualification

Added `tools/integration/iq2_s_codec_oracle.py`, which walks IQ2_S block bytes
with a standalone scalar decoder. It reads the canonical 1,024-entry grid from
the pinned ggml header but independently applies the byte indices, per-group
scales, signs and output placement. Its synthetic self-check covered all 1,024
grid indices with three sign-bit positions (3,072 cases). On the actual layer-2,
expert-174 gate/up payloads, it decoded all 3,276,800 IQ2_S values bit-for-bit
against the GGML `to_float` arrays dumped by the parity executable. The same
check applied a separate scalar IQ4_NL nibble decoder to the 1,638,400 down
values. All 4,915,200 decoded values matched exactly; combined decoder output
SHA256 is `5c7a752f019b0fcb6dfa41716637ffba76daae00edbf054f91f4a2fd02f3d83d`.
Temporary GGML arrays were written under `/tmp` and are not retained in Git.

This comparison independently checks traversal and scale/sign/code placement
against ggml's implementation, but shares the canonical IQ2_S grid constants
and IQ4_NL symbol list. It qualifies those real weight bytes for the next CUDA
adapter step; it does not qualify Q8_1 dot arithmetic or NInfer dispatch.

This is a pre-integration Strata baseline and fixture qualification. It does
not exercise any NInfer-derived IQ2_S/IQ4_NL code, prove whole-model support,
or establish a performance benefit. The generated-input run is supplemental;
the held captured activation is the model-input check. The follow-up adapter
used an independent scalar byte traversal and explicit dispatch evidence; its
operator and service smoke are documented in the
[adapter report](../2026-11-04-e4-iq2s-iq4nl-service-smoke/README.md). The
measurements above remain the pre-adapter Strata control.

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
python3 tools/integration/iq2_s_codec_oracle.py \
  --ggml-common third_party/ggml/ggml-common.h --self-test \
  --model-shard ~/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --layer 2 --expert 174 --reference-dir /tmp/e0-iq2s-iq4nl-ggml-reference
```

Before the final command, create `/tmp/e0-iq2s-iq4nl-ggml-reference` and rerun
the second `native_expert_parity` command above with
`--dump-f32-dir /tmp/e0-iq2s-iq4nl-ggml-reference` appended before layer `2`.
The raw GGML float arrays are temporary because they are model-derived data.

The source revision, executable hash, and two shard hashes are recorded beside
this report. The decoder script hash and run output are also recorded. Raw model
weights, temporary GGML float arrays, and activation payloads are not copied
into the repository.

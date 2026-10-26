# Layer-1 captured activation Q8_1 check

Date: 2026-10-26. Hardware: Jetson AGX Orin 32 GB, SM87, CUDA 12.6.
Model and task are the same Q2_0 2,048-token held-out retrieval run documented
in the parent report. This diagnostic uses the captured layer-1 activation at
prompt position 2047 (token 271) for each route.

The `.layer1.input` capture starts with a 72-byte `STMOINP1` record header;
the remaining 10,240 bytes are 2,560 little-endian float32 activation values.
Those payloads were passed separately to the existing
`native_expert_parity --q8_1-quantizer --activation-f32` checker in the
qualified Orin CUDA build. Both runs passed with zero failures:

| Captured route | Blocks | CPU/CUDA scale mismatches | CPU/CUDA code mismatches | Stored-sum mismatches |
| --- | ---: | ---: | ---: | ---: |
| CPU miss | 80 | 0 | 0 | 74 |
| Strict NInfer staged | 80 | 0 | 0 | 74 |

For each individual input, independent scale/code checks, GGML stored-sum
checks, CUDA stored-sum checks, and grouped-row checks also reported zero
errors. The 74 sum differences are the checker’s documented convention
difference: GGML stores `d * sum(q)`, while this CUDA path stores `sum(input)`.
The two captured input vectors are not bit-identical (1,747 of 2,560 values
differ; relative L2 `1.027e-7`, max absolute difference `3.576e-7`). Therefore
this check shows that each backend’s quantizer agrees on its own captured
vector. A direct cross-route comparison using the independent Python Q8_1
oracle compared all captured MoE input vectors at prompt position 2047. Layer
1 had identical FP16 scales and all 2,560 code values across its 80 blocks,
despite the small float difference. Layer 2 was the first sampled layer with
changed Q8_1 input representation: 34 of 80 scales and 103 code values
differed. Differences grew at sampled layers 3, 11 and 21. The numeric summary
is in [`cross-route-quantized-comparison.json`](cross-route-quantized-comparison.json).
This places the first sampled activation-code divergence at layer 2, but does
not identify which upstream operation causes the difference before that
boundary.

The two 10-KiB activation payloads and raw checker logs are local diagnostic
artifacts and are not tracked. Their source-capture SHA256 values are
`6b44aa553ac2ace5f0b7d056ea7ce7562a3172f7a9c77c84dd3806d83b4bf9c4` (CPU
miss) and `6f51155b69c69c99d494cca16cb4eb65f995c5b26777b8343dc3983ad0c79f70`
(NInfer staged). Both checker logs had SHA256
`0cce6c7b4892088ceedcb826ff2ae70a963553dd6ac9f6863846aedfcd491c14`.

This is a focused quantizer diagnostic, not a model-quality or performance
measurement. The unresolved CPU-miss versus staged state difference remains
open.

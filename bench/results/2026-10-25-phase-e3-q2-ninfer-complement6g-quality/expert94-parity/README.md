# Layer-3 expert 94 standalone parity replay

This diagnostic reuses the F32 MoE input captured at generated position 520
and Q2_0 weights for layer 3, expert 94 from the Q2_0 model's first shard. The
binary was `build/integration/e0-cuda-build/ninfer_q2_expert_parity`, SHA256
`6334fb6015e115ea8978f870aa6e25a2cb122761fd098a23a318b3bc1e1fd2bb`.

- Scalar NInfer D3/D4 against the independent FP64 Q2_0 reference: relative
  L2 `2.05e-7`, maximum absolute error `1.49e-8` (pass).
- Grouped resident NInfer route against Strata Q2_0/Q8_1: relative L1
  `6.706e-4` (fail; harness limit `2e-4`).
- One-entry device timing: Strata 24.689 us median, NInfer 24.152 us, ratio
  0.978×. Seven interleaved blocks showed a wide NInfer range up to 79.306 us.
- Grouped 64-token operator timing: 4,371.937 / 3,945.250 us NInfer/Strata,
  ratio 1.108×. At 128 tokens, 8,916.909 / 7,957.838 us, ratio 1.121×.

This reproduces the captured row difference outside the model server. It
separates the accurate scalar path from the grouped service path, but does not
yet isolate which grouped substage introduces the numeric difference. The
supervised process exited 2 because grouped parity checks failed; minimum
available memory was 24.12 GiB. Full process output is in
[`supervisor/stdout.txt`](supervisor/stdout.txt), with resource metadata in
[`supervisor/result.json`](supervisor/result.json).

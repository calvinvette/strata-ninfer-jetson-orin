# Joined Coder CPU-route and verifier-combine capture — Orin — 2026-10-18

This offline analysis joins two captures from the same randomized Coder IQ1_M service pair that were previously discussed separately: CPU-owned expert output at dispatch 1393/layer 1 and the verifier's post-combine `ffn_y` capture. The original model run used the exact `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M snapshot and current service binary SHA-256 `dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`; source captures and their campaign metadata remain in [the original result](../../2026-10-16-phase5-coder-q8_1-combined-moe-capture/README.md).

## Join and result

The route trace starts at dispatch 1392/layer 0 and immediately records dispatch 1393/layer 1, both for the same one-token verifier window. The layer-1 callback sequence is the same verifier run whose first `STGDIAG4` record gives position 511 and input token 271. This is the final token of the 512-token initial prompt. The CPU output records carry dispatch/layer and routed-row indices; the analyzer verifies those four records against the exact expert IDs and CPU-owner entries in dispatch 1393. Both route arms have bitwise-identical activation, expert IDs and owners for that row, and both produce the same initial request output.

The four CPU-owned experts were 209, 207, 85 and 153. Every one of their 2,560 output values differed between the default GGML CPU route and the opt-in CUDA-mirror route; relative L1 differences were 1.23%–1.57%. At the same joined verifier row (position 511, token 271), all 2,560 post-combine `ffn_y` values differed; the maximum absolute delta was `2.1168e-4` and relative L1 was `0.0040171`.

The ordered join is established by the capture call structure: `Verifier::run` invokes the pool callback in layer order for a verifier window, while the diagnostic writes `pos0` and token IDs for that same window. The raw route rows, CPU-output records and combined frame agree on dispatch, layer, row, expert IDs, owner slots, position and input token. The checked mapping is retained in `analysis.json`; raw input hashes are in `input-sha256.txt`.

This strengthens the evidence that route-dependent CPU arithmetic reaches the post-combine output on the same input row. It does not isolate each expert's weighted contribution, prove the arithmetic difference is the only cause of later persistent-state and continuation divergence, or establish a quality/performance fix. Adaptive migration remains unqualified and Phase 5 remains open.

## Reproduction

From the repository root:

```sh
python3 bench/results/2026-10-18-phase5-coder-dispatch-combine-join/analyze_join.py
sha256sum -c bench/results/2026-10-18-phase5-coder-dispatch-combine-join/input-sha256.txt
```

The analysis consumes the existing raw files in the referenced Oct 16 result. It does not launch a model or alter any capture.

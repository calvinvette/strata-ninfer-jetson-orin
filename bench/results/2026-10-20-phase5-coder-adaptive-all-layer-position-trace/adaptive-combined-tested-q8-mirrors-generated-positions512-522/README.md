# Generated-position capture with combined tested mirrors — Orin — 2026-10-20

This run used the combined opt-in Q8_1 selector documented in
[the layer-1–33 screen](../adaptive-combined-tested-q8-mirrors-layers1-33/README.md)
and captured all 48 verifier inputs at generated positions 512–522 for three
same-service 512-token prompts. It used Coder IQ1_M from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, candidate binary SHA256
`e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`, and
28-GiB per-arm supervision. Prompt cache was disabled. All 36 captures per arm
(three requests × eleven positions × 48 layers) were present.

Delayed control had identical tokens, activations, routes and raw layer-32
state at every captured position. Adaptive-cap8 had identical token IDs between
initial, intermediate and recovery requests through this 12-token output, but
accepted GDN hashes differed across all 12 initial/recovery prefixes. The first
initial-to-intermediate activation difference appeared at layer 27, position
512; raw layer-32 pre-state matched there but post-state differed. The first
intermediate-to-recovery activation difference at position 512 was layer 13.
At later positions divergence spread through more layers and routes. This
capture is the generated-position follow-up to the layer-33 boundary results.

Compact per-position route and state comparisons are in
`generated-position-analysis.json`; the token/hash summary is in
`selected-position-analysis.json`. Raw capture files are retained beneath each
arm's `result/`. Unsupported position 523 is not included: there was no
subsequent verifier dispatch after the last requested output token.

Both arms passed `MemoryMax=28G`, with minimum host/admission availability at
least 14.18 GiB and zero cgroup memory events. This is correctness evidence,
not a performance test. Phase 5 remains open.

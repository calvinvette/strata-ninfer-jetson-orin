# Combined tested Q8_1 mirrors through layer 33 — Orin — 2026-10-20

This opt-in diagnostic combined prior same-input-tested native CPU Q8_1 mirrors
for owner-migrated expert formats across layers 1–33. It used Coder IQ1_M from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, with the current candidate binary
SHA256 `e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`.
Both randomized arms used three identical 512-token prompts, 12 output tokens,
`--prompt-cache 0`, and a 28-GiB memory supervisor. This is a combined
correctness screen; the cumulative rule set is not a proposed default.

The exact selector was:

```text
iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=2,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6,iq2_s/q2_0@layer=8,iq2_s/iq4_nl@layer=9,iq2_s/q2_0@layer=10,iq2_s/iq4_nl@layer=11,iq3_xxs/q2_0@layer=12,iq2_s/q2_0@layer=13,iq2_s/iq4_nl@layer=15,iq3_xxs/iq4_nl@layer=16,iq2_s/iq4_nl@layer=19,iq2_s/iq4_nl@layer=24,iq3_s/iq4_nl@layer=27,iq3_s/iq4_nl@layer=28,iq3_s/iq4_nl@layer=29,iq3_xxs/q2_0@layer=30,iq3_xxs/iq4_nl@layer=31,iq3_xxs/iq4_nl@layer=33
```

Delayed control matched tokens, all captured position-511 inputs and routes,
and per-GDN state across all three requests. In adaptive-cap8, initial and
intermediate token IDs matched; the recovery differed in its last six of twelve
tokens. All position-511 activation inputs matched between initial and
intermediate, despite owner changes at layers 8, 13, 16, 24, 28, 29, 30 and 33.
The targeted layer-33 expert-57 output and combined layer output were bitwise
equal across the CPU-to-VRAM transition. The first-to-intermediate accepted
GDN hash mismatch began at output prefix 1; initial and intermediate differed
in GDN hashes at prefixes 1–11. Thus exact layer-32 state at the prompt tail
and exact selected position-511 inputs do not establish generated-prefix
state consistency.

The raw layer-32 verifier state at position 511 was identical across all three
adaptive requests; its raw post-state hash matched service GDN ordinal 24.
Between intermediate and recovery, the first captured activation difference
was layer 33, with later activations differing through layer 47. This transition
also had expert-ID differences only at layer 43, with owner differences at
layers 11, 27, 30, 31 and 32. The exact layer-33 Q8_1 path therefore does not
remove this later prompt-tail divergence. Captured state and service hash joins
are in `state-prefix-analysis.json`; layer 33 rows are in
`layer33-analysis.json`.

Both arms passed supervision with minimum host/admission availability of
14.15 GiB (delayed control) and 14.29 GiB (adaptive), with zero cgroup memory
events. Clocks remained dynamic; this is not performance evidence. The all-layer
position-511 route captures and raw GDN states remain in each arm's `result/`
directory. Phase 5 remains open.

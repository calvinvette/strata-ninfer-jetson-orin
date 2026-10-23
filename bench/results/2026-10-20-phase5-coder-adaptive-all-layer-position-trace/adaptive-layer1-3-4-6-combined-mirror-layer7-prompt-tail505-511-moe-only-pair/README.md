# Layer-7 QSA/MoE boundary after CPU Q8_1 mirrors — Orin — 2026-10-20

This randomized adaptive/delayed-control pair used the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M model at revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms ran 512-token short, 2,048-token long, and 512-token recovery requests
with a 12-token generation limit. Arm order was adaptive then delayed control.
The adaptive arm used the opt-in Q8_1 CPU mirror at layers 1, 3, 4, and 6 for
the measured IQ2_S/Q2_0 and IQ2_S/IQ4_NL expert pairs.

At model layer 7, the MoE verifier capture is bit-identical across adaptive
initial and recovery requests at positions 505–511: routes, router weights,
all expert rows, and combined outputs match. The all-layer dispatch trace finds
the first differing activation at model layer 9 for positions 506–511 and at
layer 10 for position 505. Layer 7 is a QSA layer in this model, so it has no
GDN recurrent state; the raw GDN-state hook rejects it, and the GDN intermediate
hook does not emit a capture there. Those unsupported selections are preserved
in the neighboring failed cells. This pair therefore makes no raw layer-7
persistent-state or GDN-intermediate claim.

Delayed control remained exact across repeated short requests and recorded
service GDN hashes. The adaptive arm still had six differing recovery token
IDs, first mismatch at position 517 (initial ID 264, recovery ID 819), with
changed terminal fingerprints in `gdn`, `ple`, `tail`, `pooled`, `pooled_full`,
`kv`, and `ple_prev`. Its first differing service GDN hash is ordinal 7 at
endpoint 511. Both supervised runs passed; minimum host/admission availability
was 14.18 GiB for adaptive and 14.31 GiB for delayed control. Across 165 and
162 memory samples, cgroup `high`, `max`, `oom`, and `oom_kill` counters were
zero. Clocks were observed but not controlled, and energy was not attributed
to requests.

The first changed activation is downstream of this QSA-layer MoE capture. The
next target is the layer-8 GDN transition, where accepted-prefix service hashes
first differ. This is correctness localization, not a performance or complete
migration result; Phase 5 remains open.

Reproduce the supported pair from the repository root with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261061 --continuations 0 --generated-tokens 12 \
  --native-cpu-q8-1-dot 'iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3,iq2_s/iq4_nl@layer=4,iq2_s/iq4_nl@layer=6' \
  --capture-moe-positions 505,506,507,508,509,510,511 \
  --capture-verify-moe-layer 7 --verify-moe-positions 505,506,507,508,509,510,511 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer1-3-4-6-combined-mirror-layer7-prompt-tail505-511-moe-only-pair
```

Raw verifier captures, route traces, service logs, memory samples, and
supervisor results are retained here. The layer-7 hook limits are described in
the adjacent failed/unsupported capture reports.

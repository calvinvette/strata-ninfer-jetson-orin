# Layer-8 mirror follow-up at the first adaptive state mismatch

This randomized short/short/short pair used prompt-cache capacity 0 and the
combined selectors `iq2_s/q2_0@layer=8,iq3_xxs/iq4_nl@layer=16`. It captured the
layer-8 MoE row, layer-9 GDN intermediates and raw state at position 511, plus
the complete layer-9 prefill trace. Both arms passed supervision. Minimum
host/admission availability was 14.12 GiB for delayed control and 14.32 GiB for
adaptive; cgroup pressure/OOM counters were zero.

The layer-9 prefill hashes and raw end state were identical at every chunk and
across all three repeated requests in both arms. Adaptive accepted-prefix
state still first differed at position 511, but per-GDN ordinal 7 through 10
(model layers 9–12) now matched. Raw layer-9 pre/post state at position 511 was
bit-identical across the adaptive requests (786,432 recurrent and 30,720
convolution values); delayed control stayed exact. The first remaining GDN
hash difference moved to ordinal 11 (model layer 14), matching the first
captured layer activation difference at layer 14.

At layer 8, expert 196 was the only changed owner row in this pair: its IDs and
input matched, while ownership changed CPU-to-GPU. The layer-8 mirror moves the
first selected activation difference from layer 9 to layer 14 and restores the
captured layer-9 raw state. At layer 13, expert 147 changes CPU-to-GPU with
matching IDs and activation; this is the next candidate for an exact-input
intervention. The adaptive arm's accepted-prefix state still differs at all 12
captured generated prefixes, although recovery token IDs match the initial
request at all 12 positions. Delayed control remains exact. The result supports a local layer-8 to
layer-9 boundary restoration; it does not qualify full state migration or
request-level correctness.

Analysis artifacts include
[`accepted-prefix-analysis.json`](accepted-prefix-analysis.json),
[`state-prefix-analysis.json`](state-prefix-analysis.json),
[`selected-position-analysis.json`](selected-position-analysis.json), and each
arm's raw layer-9 prefill, GDN intermediate, state, service, and supervisor
captures. The next experiment should add the known layer-13 IQ2_S/Q2_0 mirror
while retaining the layer-8 and layer-16 selectors, then capture layer-14 GDN
state at position 511.

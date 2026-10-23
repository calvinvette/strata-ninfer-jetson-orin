# Layer-39-only Q8_1 selector screening — Orin — 2026-10-20

This paired diagnostic applied `iq2_s/iq4_nl@layer=39` while leaving other
native CPU expert format pairs on their default arithmetic. It used the pinned
Coder IQ1_M model, seed 20261128, the same short/short/short request sequence,
and the candidate binary recorded in `campaign.json`. Both arms completed
under the supervisor: delayed control passed with 14.10 GiB minimum
host/admission availability, and adaptive passed with 14.21 GiB. Memory guard
events were zero.

The adaptive intermediate request diverged from the initial output at token
index 3, while the recovery request returned to the initial token sequence.
Because the changed arithmetic selector also reverted eligible CPU expert
pairs in every other layer to their default path, positions 521 and 522 no
longer represent matched accepted prefixes in the intermediate request. The
multi-position verifier comparator rejected the token mismatch. This run is
retained as an unsupported comparison cell; its selected-position deltas do
not isolate layer 39 and are not evidence that the layer-39 Q8_1 path caused
or fixed the earlier state change.

The next paired test keeps the prior all-layer Q8_1 setting identical at every
eligible layer except layer 39, so the effect of restoring that layer's default
path can be compared on matched tokens. No performance claim is made.

# Layer-26 first-write localization under repeated short requests — Orin — 2026-10-20

This follow-up localizes the adaptive state change found between the first and
second of three identical 512-token requests. All captures use the pinned Coder
IQ1_M GGUF and current candidate binary recorded in their campaign manifests.
The delayed-control and adaptive-cap8 arms were randomized and supervised with
the existing 28-GiB cap and six-GiB host-availability floor.

The [generated-position pair](../adaptive-short-short-short-generated-positions512-523/README.md)
first found an adaptive activation-input difference at layer 27, position 512,
with expert IDs equal and owner maps different at layers 26 and 27. State and
GDN fingerprints first differed at accepted prefix 4 between the initial and
intermediate requests; intermediate and recovery then matched exactly.

The [layer-26 MoE and raw-state capture](../adaptive-short-short-short-layer26-moe-layer26-state/)
found that at position 512 expert 213 changed CPU-to-GPU owner while its
captured expert output stayed bit-identical. At position 516 the layer-26 input
was already different, routes and router weights changed, and all ten service
expert rows differed. The captured [layer-26 raw state](../adaptive-short-short-short-layer26-moe-layer26-state/layer26-capture-analysis.json)
cross-checked to the service's GDN ordinal-20 hashes. It differed before and
after position 516, so this boundary alone did not identify the first write.

The [512–516 raw-state scan](../adaptive-short-short-short-layer26-state-prefix512-516/)
locates the first changed layer-26 state after position 515: pre-state matched,
then 786,410/786,432 recurrent values and 10,239/30,720 convolution values
differed in post-state. Delayed control matched at every captured position.
The [position-514/515 MoE, GDN and state capture](../adaptive-short-short-short-layer26-state-gdn-moe-positions514-515/)
then found layer-26 GDN field `x` as the first differing captured field at
position 515. Pre-state remained exact; post-state changed. At that token the
layer-26 activation and router weights already differed, and expert 213 changed
CPU-to-GPU owner while all ten service rows differed. Because inputs and router
weights were not equal, this does not isolate expert 213 as the cause. Its
per-layer post-state hashes cross-check to the service log.

The attempted layer-27 raw-state capture is retained as a failed diagnostic
cell in [the rejected capture record](../adaptive-short-short-short-layer26-moe-invalid-layer27-state-capture/README.md):
layer 27 is not a valid GDN state layer. No inference comparison was produced
from that attempt.

All successful arms passed supervision, with minimum host/admission
availability at or above 13.93 GiB and zero sampled cgroup memory events. These
are correctness-localization results, not a full adaptive-migration fix,
quality result or performance claim. The exact request sequence, capture files,
hash checks and reproduction commands remain with each linked run.

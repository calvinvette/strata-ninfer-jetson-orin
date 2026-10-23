# Position-522 layer-41 GDN state and intermediate capture — Orin — 2026-10-20

This supervised same-seed pair repeated the all-layer Q8_1 Coder IQ1_M
configuration with prompt cache disabled. It captured all verifier inputs,
layer-41 GDN intermediates, and raw layer-41 pre/post state at generated
position 522. Both arms passed; minimum host/admission availability was
14.13 GiB adaptive and 14.20 GiB delayed, with no cgroup memory events.

The adaptive first-to-intermediate transition already has a different raw
layer-41 pre-state before position 522: 785,998 of 786,432 recurrent values and
all 10,240 convolution-history values differ. The post-state differs in
786,266 recurrent and 10,240 convolution-history values. The first differing
captured GDN field is `h`; `x` and `qkv` are exact, while `h`, `y`, `gdn_out`,
`ffn_x`, and `ffn_y` differ. The GDN post-state hash for every request matches
the corresponding service hash at GDN ordinal 31. Intermediate-to-recovery is
bit-identical in every GDN field and raw state. Delayed control is exact across
all transitions. The all-layer verifier trace first differs at layer 41 at
position 522, and QSA state hashes at layers 43 and 47 change on
initial-to-intermediate.

This locates the state divergence before processing the position-522 token at
layer 41. It does not show where that pre-state first changed; position 521 is
the next capture, aligned with the earlier layer-40 input difference. The
comparison script is `../compare_layer41_gdn.py`; its validated results are in
`layer41-gdn-analysis.json`.

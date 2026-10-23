# Generated-position 512 layer-13 verifier, GDN and state capture

This supervised Phase 5 diagnostic used the Coder GGUF `IQ1_M` snapshot at
revision `5348543e0147355ac9cbcb031184a3546350988e`, seed `20261123`, and three
identical 512-token requests with 12 generated tokens. The adaptive selector
was enabled through layer 41; the paired arm delayed adaptation. Prompt cache
was disabled. Both arms passed supervision: minimum host/admission availability
was 14.211 GiB (adaptive) and 14.091 GiB (delayed), with zero sampled cgroup
memory events.

The verifier's CUDA-side MoE input capture contains three records at position
512 for each of the 48 layers. In the adaptive arm, initial-to-intermediate
first differs at layer 29, then intermediate-to-recovery first differs at
layer 15 (33 layers differ). Delayed control is bit-identical across all 48
layers and all three requests. Thus layer 13 is not the first changed input in
the latter transition.

At layer 13, all captured GDN intermediates (`x`, `qkv`, `h`, `gate`, `beta`,
`z`, `y`, `gdn_out`, `ffn_x`, and `ffn_y`) are bit-identical for the three
adaptive requests. Raw pre/post recurrent and convolution state is also
bit-identical, and its post-state hash matches service GDN ordinal 10 on every
request. Layer-13 MoE routes and verifier inputs are equal as well. Delayed
control is exact at these captures.

An earlier CPU-pool trace appeared to show a large layer-13 activation change
on recovery. That row had no CPU-owned experts, however, so the verifier had
not needed to materialize the activation in the host CPU buffer; the trace had
serialized stale host data. The trace writer now emits `activation_valid` and
only marks an activation valid when that row has a CPU-owned expert. The
original capture remains in the result directory as evidence of the diagnostic
failure; it must not be treated as an actual layer-13 activation delta.

This narrows the next Phase 5 boundary to layer 15 for the intermediate-to-
recovery transition. It does not attribute that input change to an operator or
prove full accepted-prefix transaction equivalence. The previous layer-12
boundary pair and its reproduced inputs remain separate artifacts.

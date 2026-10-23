# Layer-29 mirror follow-up with no prompt cache

This randomized short/short/short pair used prompt-cache capacity 0 and
selectors at layers 8, 13, 16, 24, 28, and 29. It captured layer-30 prefill and
raw verifier state, layer-29 verifier MoE output, and all-layer dispatches at
position 511. Both arms passed supervision. Minimum host/admission availability
was 14.12 GiB for adaptive and 14.27 GiB for delayed control; cgroup
pressure/OOM counters were zero.

Layer-30 prefill hashes and raw state matched at every chunk and across all
three requests. Raw layer-30 verifier state at position 511 was also
bit-identical across both adaptive transitions (786,432 recurrent and 30,720
convolution values); delayed control was exact. Despite that local state
parity, accepted-prefix fingerprints differ at all 12 adaptive positions.
The first activation difference in the initial/recovery trace moved from
layer 30 to layer 31 (relative L2 0.00999; maximum absolute delta 0.02904).

At layer 30, experts 121 and 212 are the only owner changes in the captured
pair; both move CPU-to-GPU with matching IDs and input activations. The native
pack's layer-30 profile is IQ3_XXS/Q2_0, matching the supported selector pair.
The delayed-control arm remained exact. Adaptive recovery still differs from
initial by 6 of 12 token IDs. This is another narrow boundary restoration, not
accepted-state or request-level qualification. The next experiment adds the
layer-30 selector and captures layer-32 GDN state beyond the intervening QSA
layer 31.

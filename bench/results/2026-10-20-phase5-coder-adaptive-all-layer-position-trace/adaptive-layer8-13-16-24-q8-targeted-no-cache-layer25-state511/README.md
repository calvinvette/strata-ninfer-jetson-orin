# Layer-24 mirror follow-up with no prompt cache

This randomized short/short/short pair used prompt-cache capacity 0 and
selectors at layers 8, 13, 16, and 24. It captured layer-25 prefill and raw
verifier state, layer-24 verifier MoE output, and all-layer dispatches at
position 511. Both arms passed supervision. Minimum host/admission availability
was 14.14 GiB for adaptive and 14.30 GiB for delayed control, with zero cgroup
pressure/OOM events.

Layer-25 prefill hashes and raw state matched at all chunks and across all
three repeated prompts. Raw layer-25 verifier pre/post state at position 511
also matched across both adaptive request transitions (786,432 recurrent and
30,720 convolution values); delayed control was exact. The accepted-prefix
trace still differed: adaptive per-GDN hashes first changed at ordinal 22
(model layer 29) for initial-to-intermediate and ordinal 21 (model layer 28)
for intermediate-to-recovery. The first initial-to-recovery activation
difference was layer 29 (relative L2 0.00342, maximum absolute delta 0.00730).

At layer 28, experts 146 and 36 are the only captured owner changes; both move
CPU-to-GPU with matching IDs and activation inputs. The native pack's layer-28
profile is IQ3_S/IQ4_NL, making `iq3_s/iq4_nl@layer=28` the next narrow mirror
candidate. At layer 24, expert 173 still changes CPU-to-GPU, but its exact
layer-24 selector leaves layer-25 raw state exact. The adaptive arm's recovery
differs from initial by 6 of 12 token IDs and accepted-prefix state differs at
all 12 prefixes. Delayed control remains exact. The evidence localizes the next
boundary to layer 28/29 but does not isolate either layer-28 row as causal.

Raw and derived evidence is retained in the two arm directories and
[`selected-position-analysis.json`](selected-position-analysis.json),
[`accepted-prefix-analysis.json`](accepted-prefix-analysis.json), and
[`state-prefix-analysis.json`](state-prefix-analysis.json). The next pair adds
the layer-28 IQ3_S/IQ4_NL selector and captures layer-29 state at position 511.

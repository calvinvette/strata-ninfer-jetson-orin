# Layer-18 owner capture after the layer-5 mirror — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used seed `20261081`, the
layer-5 mirror selector, and the pinned Coder IQ1_M GGUF at revision
`5348543e0147355ac9cbcb031184a3546350988e`. Candidate binary SHA256:
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Both
arms used the 512/2,048/512 same-service sequence with 12 generated tokens per
request and a 28-GiB supervisor.

Delayed-control initial/recovery remained exact across selected activations,
routes, token IDs and state fingerprints. In adaptive-cap8, recovery token IDs
matched initial at all 12 positions, but accepted-state and GDN hashes differed
at every prefix. The first captured activation difference remained layer 19
for positions 506–511 and layer 27 for position 505.

At layer 18, positions 506–511 have matching expert IDs, inputs and router
weights; IQ3_XXS/IQ4_NL expert 110 alone changes CPU-to-GPU owner and output.
The combined MoE output differs at all 2,560 values at each position. The GDN
capture first differs at `ffn_y` for positions 506–511; position 505 is exact.
Raw recurrent and convolution state at accepted position 511 is exact across
initial/recovery.

The independent single-row native expert oracle used the exact captured
position-506 activation. Both the initial CPU service row and recovery GPU
service row match their corresponding oracle outputs bit-for-bit. CPU/GPU
outputs differ by 1.5597% relative L2. This joins the row-level owner-dependent
arithmetic difference to the service capture for one expert and position. It
does not explain why adaptive residency changes or resolve the remaining
accepted-state mismatch. The next pair adds the layer-18 IQ3_XXS/IQ4_NL mirror
to check whether the layer-19 input is restored.

The retained analyses are `selected-position-analysis.json`,
`layer18-moe-analysis.json`, `layer18-gdn-analysis.json`,
`layer18-state-analysis.json`, and
`expert110-layer18-position506-oracle/oracle-join.json`. Both arms passed with
minimum host/admission availability 14.24 GiB for delayed-control and 14.29
GiB for adaptive-cap8, above the six-GiB floor, and zero cgroup memory events.
Clocks were observed but not controlled; energy was not attributed. This is
correctness evidence, not a performance or quality comparison.

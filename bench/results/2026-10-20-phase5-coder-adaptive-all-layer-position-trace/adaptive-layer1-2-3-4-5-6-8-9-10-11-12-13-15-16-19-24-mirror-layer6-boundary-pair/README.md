# Layer-5 mirror follow-up — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used seed `20261080` and added
the IQ2_S/IQ4_NL layer-5 rule to the layer-specific selector from the prior
capture. It used the pinned Coder IQ1_M GGUF at revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. The
same-service sequence was 512/2,048/512 tokens with 12 generated tokens per
request under separate 28-GiB supervisors.

The layer-5 mirror made all seven selected expert rows, combined outputs, GDN
intermediates, and raw pre/post recurrent and convolution state at position 511
bit-identical across adaptive initial/recovery. Adaptive token IDs now match
at all 12 positions, but accepted-state and GDN hashes still differ at every
prefix. The first selected activation difference is layer 19 at positions
506–511 and layer 27 at position 505. Delayed-control initial/recovery remains
exact.

For positions 506–511, the first changed owner before layer 19 is expert 110 at
layer 18 (IQ3_XXS/IQ4_NL), moving CPU-to-GPU with matching expert IDs. A
standalone native parity run on the exact layer-18 position-506 activation
reported a 1.57% CPU/GPU relative-L2 output delta. This pair did not capture
layer-18 per-expert service outputs, so the standalone result is not yet joined
to the service row. The retained oracle files are under
`expert110-layer18-position506-oracle/`. A fresh direct layer-18 service capture
is needed before attributing the layer-19 activation delta to that row.

The layer-5 service comparisons are in `layer5-moe-analysis.json`,
`layer5-gdn-analysis.json`, `layer5-state-analysis.json`, and
`selected-position-analysis.json`. Both arms passed supervision with minimum
host/admission availability of 14.20 GiB for adaptive-cap8 and 14.29 GiB for
delayed-control, above the six-GiB floor, and zero cgroup memory events. Clocks
were observed but not controlled; energy was not attributed. This is
correctness localization, not a performance or quality comparison.

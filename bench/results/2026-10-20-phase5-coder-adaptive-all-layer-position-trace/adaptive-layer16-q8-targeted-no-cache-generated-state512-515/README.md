# Layer-17 accepted-state trace with the layer-16 selector and no prompt cache

This randomized short/short/short pair used the pinned Coder IQ1_M GGUF,
current binary SHA256 `d31a4e7c…2078b1`, and selector
`iq3_xxs/iq4_nl@layer=16`. `--prompt-cache 0` forces all three identical
512-token prompts to be recomputed. The override is optional in the harness and
does not change its default. Both arms passed their 28-GiB supervisors; minimum
host/admission availability was 14.14 GiB for adaptive and 14.22 GiB for
delayed control, with zero cgroup pressure/OOM events.

The companion
[`repeated prefill trace`](../adaptive-layer16-q8-targeted-prefill-no-cache-retry/README.md)
found all layer-17 GDN chunk hashes and raw end-of-prompt state identical across
all three requests in each arm. This run captured raw layer-17 verifier state
at positions 512–515 and checked every post-state byte hash against its service
GDN hash. Delayed control was bit-identical across both same-service request
transitions at all four positions. In adaptive, raw pre-state and post-state
already differed between the first and second request at position 512, with
786,386/786,432 recurrent and 10,240/30,720 convolution values changed in the
pre-state; both state components were almost entirely different at later
positions. The request token IDs at position 512 still matched.

The accepted-prefix trace independently found the first adaptive persistent
fingerprint mismatch at position 511, before the captured position-512 state.
At that prefix the `gdn`, `kv`, `pooled`, and `pooled_full` fields differ, and
per-layer GDN hashes first differ at ordinal 7 (model layer 9). The all-layer
dispatch trace also first differs at layer 9 at position 511. At the preceding
layer 8, expert 196 changes CPU-to-GPU owner while IDs and activation input
match. The exact-input oracle and layer-8 mirror qualification are recorded in
[`the prior layer-8 report`](../adaptive-layer1-3-4-6-combined-mirror-layer8-prompt-tail505-511-pair/README.md).
This motivates the layer-8 mirror follow-up below; it does not assign the
whole request divergence to that row.

In the adaptive arm, initial and intermediate request tokens match, but
recovery differs at 9 of 12 token positions. Delayed-control tokens and
accepted-prefix fingerprints remain exact across all three requests. Raw
verifier GDN state and accepted-prefix/service hashes are direct evidence; the
all-layer trace contains initial and recovery blocks only. This is a narrow
state-localization result, not a migration fix or performance result.

# Repeated layer-17 prefill trace with prompt caching disabled

This cache ablation reruns the randomized short/short/short adaptive-versus-
delayed-control sequence with `--prompt-cache 0` and the layer-16 selector
`iq3_xxs/iq4_nl@layer=16`. The diagnostic runner's default prompt-cache setting
is unchanged; this override exists only for the experiment. Both arms passed
supervision. Adaptive minimum host/admission availability was 14.23 GiB and
delayed-control minimum was 14.09 GiB; cgroup pressure and OOM counters stayed
zero.

Each of the three requests performed a full 511-token prefill. For layer 17
(GDN ordinal 13), the eight chunk hashes and raw end-of-prompt state were
identical across all three prefill passes in each arm: 786,432 recurrent and
30,720 convolution values matched bit-for-bit. The adaptive arm nevertheless
returned different recovery tokens from its first request; delayed-control
tokens remained exact. Thus the tested prefill boundary is reproducible, while
the adaptive history effect occurs after that captured boundary or in a later
state handoff. Because prompt caching was disabled, the runtime correctly did
not emit its session-level state fingerprints; this capture makes no accepted-
state parity claim.

The first no-cache attempt in the sibling
[`adaptive-layer16-q8-targeted-prefill-no-cache`](../adaptive-layer16-q8-targeted-prefill-no-cache/)
was retained as a failed harness cell: its old validator required session
hashes even though the runtime suppresses those hashes when caching is off. The
runner now records their absence explicitly and preserves trace-only results.
The subsequent
[`adaptive-layer16-q8-targeted-no-cache-generated-state512-515`](../adaptive-layer16-q8-targeted-no-cache-generated-state512-515/)
adds raw verifier-state and accepted-prefix captures.

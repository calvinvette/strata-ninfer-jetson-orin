# Layer-41 expert-171 mirror and layer-42 state follow-up — Orin — 2026-10-20

This randomized same-service pair extends the cumulative opt-in Q8_1 selector
through `iq3_xxs/iq4_nl@layer=41`. It used Coder IQ1_M from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, candidate binary SHA256
`e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`, and
seed `20261119`. Each arm sent three 512-token prompts requesting 12 outputs,
with prompt cache disabled and a 28-GiB memory supervisor.

At generated position 512 (token 760), layer-41 expert 171 (IQ3_XXS/IQ4_NL)
moved CPU-to-VRAM between adaptive initial and intermediate requests while
its input and route IDs matched. The captured activation SHA256 is
`47dcc30d729b6312ac22407f4baf492b45b1921a5628f353b66c59697d2f7b05`. The
default standalone CPU/CUDA outputs differed in all 7,680 words at 1.21%
relative L2. The targeted Q8_1 oracle outputs matched bitwise. The actual
service CPU row matched the Q8_1 oracle within relative L2 `1.61e-9`; see
`operator-oracle/layer41-expert171/oracle-join.json`.

Delayed control remained exact. In adaptive-cap8, the initial/intermediate
position-512 activations matched at all 48 layers. The layer-41 owner transition
remains in the route trace, while raw layer-42 GDN pre/post state was exact and
its post-state hash matched service ordinal 32. The first changed position-512
activation for intermediate-to-recovery was layer 13. Accepted GDN hashes
still differed at all 12 initial/recovery prefixes even though all 12 output
tokens matched. This confirms a local operator/state boundary and the continued
request-history state divergence; it does not qualify the migration path.

Both arms passed supervision with minimum host/admission availability of
14.16 GiB (delayed control) and 14.29 GiB (adaptive), with zero cgroup memory
events. Clocks remained dynamic; no performance claim is made. Raw route, row,
verifier, state and service captures plus their analyzers are retained in this
directory. Phase 5 remains open.

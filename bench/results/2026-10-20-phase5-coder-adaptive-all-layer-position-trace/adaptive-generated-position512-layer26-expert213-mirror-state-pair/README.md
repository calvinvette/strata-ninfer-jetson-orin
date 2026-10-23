# Layer-26 expert-213 mirror and generated-position state capture — Orin — 2026-10-20

This supervised randomized pair followed the first generated-position
mismatch found with combined tested CPU Q8_1 mirrors. It used Coder IQ1_M from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, current candidate binary SHA256
`e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`, and
seed `20261117`. The three 512-token prompts requested 12 outputs; prompt cache
was disabled and each arm ran under a 28-GiB memory supervisor.

At generated position 512 (token 760), layer-26 expert 213 (IQ2_S/IQ4_NL)
changed CPU-to-VRAM owner between adaptive initial and intermediate requests.
Its activation, route IDs and weights matched. On the captured FP32 activation
(SHA256 `c8c8e99bf554aad386045500bbf42af7427489b8ea9bc31f38a5b396abd67359`),
the standalone default CPU/CUDA outputs differed in all 7,680 words at 1.49%
relative L2. The targeted `iq2_s/iq4_nl@layer=26` Q8_1 path matched CPU and
CUDA outputs bitwise. The actual service CPU row matched the Q8_1 oracle to
relative L2 1.20e-9 (JSON capture serialization accounts for the tiny
nonzero delta).

At layer 26, raw pre/post GDN state was exact across the initial/intermediate
transition and matched its service hash at GDN ordinal 20. Delayed control was
exact. The all-layer trace's first adaptive activation difference at position
512 moved from layer 27 (with the earlier rule set) to layer 41 after adding
this layer-26 rule. The initial/intermediate token IDs stayed equal, while
accepted state hashes first differed at prefix 1. On the intermediate-to-
recovery transition, layer-26 pre-state still matched but post-state changed
in 786,424/786,432 recurrent values and 10,240/30,720 convolution values;
recovery tokens still matched in this 12-token sample. Thus the operator/state
boundary was repaired for one request transition and moved elsewhere, but
adaptive accepted-prefix parity remains unqualified.

The position-512 route trace also exposed layer-40 expert 114 (IQ3_S/IQ4_NL)
with identical activation and route IDs but CPU-to-VRAM ownership change. A
same-input standalone oracle on that activation measured a 1.33% CPU/CUDA
relative-L2 difference; `iq3_s/iq4_nl@layer=40` made that expert output
bit-identical. Its activation and oracle records are retained with the
[layer-40 service mirror pair](../adaptive-generated-position512-layer40-expert114-mirror-state-pair/README.md).
The earlier expert-213 oracle files are under
`operator-oracle/layer26-expert213/`.

Both arms passed supervision with minimum host/admission availability of
14.188 GiB (adaptive) and 14.322 GiB (delayed control), with zero cgroup memory
events. Clocks were dynamic; no performance claim is made. `campaign.json`,
raw activation/routes/output captures, raw GDN state, service logs and state
hash join are retained here. Phase 5 remains open.

# Layer-31 position-519 owner transition — Orin — 2026-10-22

This supervised adaptive-only replay repeated the pinned Coder IQ1_M
`short-512 → long-2048 → short-512` sequence with 128 generated tokens and
`STRATA_NATIVE_CPU_Q8_1_DOT=all`. The current service completed successfully;
the raw all-layer dispatch trace contains both initial and recovery records at
position 519 for token 5639.

Layer-31 verifier input, route IDs and route weights are bit-identical across
the initial and recovery requests. Four routed experts change owner from CPU
to CUDA (IDs 76, 22, 198 and 210). Only expert 22's output row changes in the
captured verifier parts: 2,559/2,560 values differ (relative L2
`1.31996e-4`). The shared and combined layer-31 output changes in 2,555/2,560
values (relative L2 `3.21558e-5`), matching the changed post-layer `bo` in the
position-519 boundary capture. This links the previously observed layer-32
input/state onset to an owner-dependent layer-31 output for this same token.

The exact 2,560-value activation was extracted from the verifier input capture
(SHA256 `bf609469743a057a07de8b514bf616399e84fe79fc84f71ca643cfe9f950e824`).
The independent `native_expert_parity` harness ran expert 22 at layer 31 with
`STRATA_EXP_MODE=0` and selector
`STRATA_NATIVE_CPU_Q8_1_DOT=iq3_xxs/iq4_nl@layer=31`. The initial service CPU
row matched the independent CPU output bit-for-bit; the recovery service CUDA
row matched the independent CUDA output bit-for-bit. Thus each service owner
matches its same-input oracle, while those CPU and CUDA rows differ. This is
operator correctness evidence for one captured activation, not a general
accepted-state fix or performance result. A reciprocal-SiLU arithmetic
variant has matched CPU/CUDA on this same activation in a prior isolated
oracle run, but a service-level state-recovery result is still required before
considering it as a candidate.

The supervised service run took 597.3 seconds, with 14.17 GiB minimum host and
admission availability and zero cgroup memory events. Dynamic CPU/GPU clocks
were sampled; EMC readback was unsupported and energy was not measured. Raw
dispatch/input/output captures and oracle dumps remain local.

# IQ4_XS/IQ4_NL mixed resident expert route

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This completes the
experimental CUDA codec-pair selector for the two inventoried mixed artifacts.
The grouped path decodes GGML IQ4_XS gate/up blocks, quantizes the SwiGLU
activation to Q8_1, and uses the existing IQ4_NL down path at 2560/640.

## Operator check

Actual Coder IQ1_M layer 47/expert 5 weights dispatched once. Against Strata,
gate/up values and all 720 hidden Q8_1 bytes matched exactly. The final output
relative L2 was `8.85e-8`, relative L1 `6.12e-8`, and max absolute error
`1.49e-8`. The activation row was captured from a different layer, not from
layer 47; this is a real-weight operator check, not a paired layer activation
oracle. See [`ninfer-parity.log`](ninfer-parity.log).

## Strict full-model dispatch checks

A strict Coder IQ1_M request using the temporary layer-1-first profile traversed
the full verifier and generated token `4`. It logged the experimental route at
each mixed tuple encountered, including IQ4_XS/IQ4_NL at layer 47. No strict
unsupported-codec error occurred. Minimum available physical memory was 20.56
GiB; the cgroup OOM-kill counter stayed at its preexisting value of one.

The same one-token strict request passed against the actual ISTA-DASLab IQ3_S
artifact with its matching `iq3-s-pack` and 512-expert profile. It also logged
all mixed tuple routes, including IQ4_XS/IQ4_NL at layer 47, and generated
`4`. Minimum available memory was 19.66 GiB; the OOM-kill counter did not
increment. Both service runs validate strict traversal and dispatch only. They
were not paired against Strata, do not establish answer quality or persistent
state equivalence, and are not performance measurements. Raw supervised
records are in [`service-strict-run/`](service-strict-run/) and
[`service-ista-strict-matching-pack/`](service-ista-strict-matching-pack/).
An initial ISTA launch used the 256-expert Coder pack and exited before loading
the model because the pack geometry did not match the 512-expert artifact. Its
raw failure is retained in [`service-ista-strict/`](service-ista-strict/); it
is a setup error and not a backend failure.

## Current mixed-codec boundary

All observed Coder IQ1_M and ISTA IQ3_S layer tuples now have an experimental
CUDA resident route: IQ2_S/IQ4_NL, IQ3_XXS/IQ4_NL, IQ3_S/IQ4_NL,
IQ2_S/Q2_0, IQ3_XXS/Q2_0, IQ3_S/Q2_0 and IQ4_XS/IQ4_NL. Strict traversal
passed for one short request on each artifact. The operator activation checks
for the three Q2_0-down tuples and IQ4_XS use rows captured at other layers;
there is only one real-weight operator check per tuple. These results do not
qualify every layer, prompt quality, persistent state, grouped prefill,
staging/missing-expert execution, speed, HIP or SYCL. NInfer remains opt-in and
Strata remains the default.

The final CUDA build used one job in `build/integration/e0-cuda-build`. The
`strata` binary SHA256 was
`42fbb0afd69eb11979884352584a5f14f141b3e3ed5a6e87eef4a780aa721b2c`; the
`ninfer_iq_expert_parity` binary SHA256 was
`f11c17399d7dbde7dc60315e79c82d4ab4eb243e4eca330184e5e6981f20f833`.

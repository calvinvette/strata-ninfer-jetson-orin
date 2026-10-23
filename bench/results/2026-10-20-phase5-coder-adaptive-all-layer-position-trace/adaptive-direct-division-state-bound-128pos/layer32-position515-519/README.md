# Adaptive position-519 state onset — Orin — 2026-10-22

This supervised, same-binary delayed-control/adaptive pair repeated the pinned
Coder IQ1_M `short-512 → long-2048 → short-512` sequence with 128 generated
tokens per request, seed `20261082`, and `STRATA_NATIVE_CPU_Q8_1_DOT=all`.
Binary SHA256: `ce53a56cf1d807764bf5eadc2555c35abd1cd69684f33a8393c655c475653dcb`.
The model revision and shard hashes are inherited from the pinned pair in the
parent directory. Each arm passed supervision and workload validation.

The full accepted-prefix service-hash scan had identified position 519,
model GDN layer 32, as the first changed hash. Raw layer-32 commits confirm
that boundary: positions 515–518 are bit-identical between the initial and
recovery short requests, while at position 519 564,534/786,432 recurrent
values differ (relative L2 `1.2833e-7`, maximum absolute difference
`8.94e-8`). Its 30,720 convolution-history values remain exact. Accepted token
IDs are equal at each sampled position, including 519. All ten captured raw
commit records match the corresponding service GDN hashes. The delayed-control
arm is bit-exact across all five positions.

At position 519, all-layer verifier inputs match through model layer 31; layer
32 is the first changed input (2,554/2,560 values, relative L2
`1.4294e-5`). The layer-31 boundary has an exact residual `R` and `inj2`, but
its post-layer `bo` changes in 2,555/2,560 values (relative L2 `3.3842e-5`).
The subsequent layer-32 read changes `xn` in 8,316/10,240 values (relative
L2 `1.0751e-5`). At layer 32, `x` is the first changed captured GDN field;
`qkv`, `h` and `z` are exact, while later intermediates and `ffn_y` differ.
Verifier pre/post GDN states cross-check exactly against adjacent committed
states for both requests and both arms. Delayed control remains exact in every
captured boundary and intermediate.

Layer-32 route IDs remain equal at position 519, but the captured router
weights differ slightly; all ten expert rows and the combined MoE output then
differ. Those are downstream of the already changed layer-32 input and do not
identify its source. The next targeted capture is layer-31 dispatch ownership,
routes and expert output at position 519, followed by a same-input independent
CPU/CUDA expert oracle if an owner-dependent row changes.

Adaptive recovery still first differs from the initial response at generated
output index 47 (73/128 IDs differ overall). The position-519 state onset
precedes that first token difference by a wide margin. The adaptive and
delayed arms took 599.5/602.5 seconds; each had 14.18 GiB minimum host and
admission availability and zero cgroup high/max/OOM events. CPU/GPU clocks
were sampled dynamically, EMC readback was unsupported, and energy was not
measured. Capture copies add runtime overhead, so these are correctness
measurements only. Raw captures and service logs remain local.

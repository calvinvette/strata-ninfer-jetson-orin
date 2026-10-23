# Verifier inputs at position 534 across all model layers — Orin — 2026-10-22

This supervised adaptive-only rerun used the same pinned Coder IQ1_M
short→long→short sequence, 128 generated tokens per request, adaptive cadence
4/cap 8, direct-division CPU path, and `STRATA_NATIVE_CPU_Q8_1_DOT=all` as the
parent campaign. At position 534, the service captured the verifier input for
all 48 model layers in both the initial and recovery short requests. The token
was 3155 in both captures at every layer. The raw file contains 96 records.

Inputs at model layers 0 through 21 are bit-exact across the two requests. The
first changed input is layer 22: all 2,560 values differ, with relative L2
`3.7883e-4`. The input difference then grows through later layers. Together
with the all-layer committed-state capture, which found layer 22 to be the
first changed GDN state at the same accepted position, this narrows the onset
to the output path of layer 21 feeding layer 22. It does not yet identify
whether the layer-21 MoE owner/output, another layer-21 operation, or their
combination causes the change.

The wrapper completed all three 128-token requests in 596.9 seconds. Minimum
host/admission availability was 14.14 GiB, above the six-GiB floor; cgroup
memory-event counters remained zero. Dynamic CPU/GPU clocks were sampled,
EMC readback was unsupported, and energy was not measured. This is correctness
localization only. The raw `verify-moe-input.bin` and service records remain
local. `layer-input-summary.tsv` is the compact comparison.

The next experiment should capture layer-21 dispatch owners and same-input
CPU/GPU outputs at position 534, then check the exact rows against the
independent native expert oracle. Keep the all-layer GDN state hash audit as a
separate check from the activation comparison.

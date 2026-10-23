# Layer-12/13 residual boundary capture — Orin — 2026-10-20

This randomized same-service pair used the pinned Coder IQ1_M model revision
`5348543e0147355ac9cbcb031184a3546350988e`, candidate binary SHA256
`70374afa9a70b40ec08b14ee9c4e925e23c8b1a7e2b31d187b4aa753fe76e05b`, seed
`20261122`, three 512-token requests, 12 generated tokens, no prompt cache,
and the established Q8_1 selector through layer 41. It captures residual `R`,
pending write `bo`, inject `inj2`, and the next layer's `R`/`xn` around the
layer-12/13 boundary at generated position 512.

Both delayed-control and adaptive-cap8 runs passed. Each arm produced three
boundary records. All eight captured fields were bit-identical across the
initial, intermediate, and recovery requests, including layer 13's first
hyperconnection read output. In the adaptive arm, the all-layer route-input
trace still differs at layer 13: its 2,560-value activation differs in every
element between initial and recovery (maximum absolute difference 1.8666),
while the selected expert IDs match. Thus the sampled layer-12 residual and
pending fields and layer-13 first read output do not explain the later layer-13
GDN input difference. The capture does not include the GDN mix vector `mixed_`
or layer-13 GDN state; those remain the next diagnostic targets.

The adaptive and delayed arms completed in 103.2 s and 100.0 s, with minimum
host/admission availability of 14.065 GiB and 14.269 GiB respectively; both
had zero cgroup memory events. Full records, raw binaries, logs, and launch
commands are retained in the arm directories. The first instrumentation run,
in the sibling `adaptive-generated-position512-layer12-boundary-capture/`
directory, failed before comparison because an offset placed the pre-read
snapshot beyond its pinned buffer. That failed cell is retained; the offsets
were corrected, the CUDA build and focused tests passed, and this retry
produced the validated records. No performance claim is made. Phase 5 remains
open.

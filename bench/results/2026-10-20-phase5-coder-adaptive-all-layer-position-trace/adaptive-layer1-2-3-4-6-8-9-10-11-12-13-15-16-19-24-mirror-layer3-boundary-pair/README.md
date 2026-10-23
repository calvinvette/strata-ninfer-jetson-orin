# Layer-2 mirror boundary follow-up — Orin — 2026-10-20

This randomized delayed-control/adaptive pair used seed `20261078` and added
the IQ2_S/IQ4_NL layer-2 rule to the layer-specific selector from the
[layer-2 capture](../adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer2-boundary-pair/README.md).
It used the pinned Coder IQ1_M GGUF at revision
`5348543e0147355ac9cbcb031184a3546350988e` and candidate binary SHA256
`d31a4e7c8d7f96e0ec9de906d4e148470920a9063b17e3611d3a0ebd7c2078b1`. Each
arm ran the 512/2,048/512 same-service sequence and generated 12 tokens per
request under a 28-GiB supervisor.

The mirror made all seven captured layer-2 expert rows, combined MoE outputs,
GDN intermediate fields, and route/weight records bit-identical between
adaptive initial and recovery. Raw layer-2 pre/post state at accepted position
511 was also exact. The delayed-control arm remained exact throughout. The
mirror did not restore adaptive full-request parity: all 12 recovery token IDs
and all accepted-state/GDN hash prefixes still differed. The first captured
activation difference moved to layer 6 for positions 506–511 and to layer 27
for position 505. This confirms a narrow layer-2 boundary correction while
showing that a downstream or separate divergence remains; it is not a
migration fix or a quality/performance result.

Derived files are `selected-position-analysis.json`, `layer2-moe-analysis.json`,
`layer2-gdn-analysis.json`, and `layer2-state-analysis.json`. Both services
passed supervision with minimum host/admission availability 13.98 GiB for
delayed-control and 14.25 GiB for adaptive-cap8, above the six-GiB floor, and
zero cgroup `high`, `max`, `oom`, or `oom_kill` events. Clocks were observed
but not controlled; energy was not attributed to requests.

The next capture targets layer 5, immediately before the changed layer-6
activation rows, to locate the earliest remaining boundary. Position 505's
later layer-27 difference may have a distinct path and is retained separately
in the all-layer trace.

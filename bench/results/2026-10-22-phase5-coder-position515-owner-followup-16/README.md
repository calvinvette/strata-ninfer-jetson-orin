# Short-chain ownership control at position 515 — Orin — 2026-10-22

This same-seed control captured all-layer dispatch ownership at position 515
for the held-out Coder IQ1_M open-response prompt in three same-service
512-token requests. Both delayed-control and cap-8 adaptive arms generated 16
tokens per request; model, binary and workload identities are in
`campaign.json`. The supervisor passed both arms in 101.02 and 96.56 seconds,
with 14.05 and 14.19 GiB minimum host/admission availability and zero sampled
cgroup low/high/max/OOM/OOM-kill events.

The adaptive arm changed CPU/GPU owner classification across request history
at model layers 1, 4, 8, 9, 11, 14, 16, 20, 26, 28, 30, 31, 33, 35, 37, 39,
40, 41 and 45. At layer 21, routes and expert IDs remained unchanged and no
owner change was observed. All 16 accepted-prefix token IDs and state/GDN
fingerprints matched between initial and recovery requests. Delayed control
also had exact tokens/state and no selected owner changes. Several activations
are marked unknown because the capture did not retain CPU-owned activation
rows for those layers; this check is an ownership trace, not a full numerical
operator comparison.

This rules out the layer-21 owner transition at position 515 for the short
16-token request sequence. That sequence does not reproduce the state drift
seen after 256-token requests, so it cannot explain the long-chain result. The
next diagnostic captures the same all-layer owner data in the full 256-token
adaptive sequence while reusing its independently hash-verified layer-22 raw
state evidence.

`selected-position-analysis.json`, service logs, captured dispatch records and
28-GiB supervisor telemetry are retained here. Clocks were observed
dynamically; EMC readback and request-attributed energy were unavailable. No
default or profile changed.

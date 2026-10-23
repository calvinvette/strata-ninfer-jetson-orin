# Rejected GDN-state hook selection for layer 3 — Orin — 2026-10-20

This retained failed attempt reused seed `20261077` and the short→short→short
adaptive/delayed sequence intended to test the layer-24 mirror context shift.
Startup rejected the diagnostic setup before requests began because model layer
3 is not a valid raw GDN-state capture layer. The engine log records
`GDN state capture needs a valid GDN layer, path, and token positions`; the
supervisor had no OOM or cgroup pressure events and stayed above the six-GiB
availability floor.

No correctness conclusion is drawn from this attempt. The corrected rerun
moved only the GDN state and commit capture to model layer 4 while retaining
the layer-3 MoE capture; see the sibling
[`state4` pair](../adaptive-layer24-short-short-short-no-cache-layer3-state4-pair/README.md).

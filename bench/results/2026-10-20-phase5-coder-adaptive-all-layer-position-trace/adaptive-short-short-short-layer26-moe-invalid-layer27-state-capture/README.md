# Rejected layer-27 GDN state capture — Orin — 2026-10-20

This was a diagnostic setup attempt while following the adaptive short-request
state difference. The engine rejected `--capture-verify-gdn-state-layer 27`
because layer 27 is not a valid GDN state layer. The delayed-control service
exited before readiness; no request or inference comparison was completed.
The run stayed above the six-GiB host-availability floor and sampled no cgroup
memory events. This failed hook selection is retained to distinguish an
unsupported diagnostic cell from a model or runtime failure. A valid layer-26
capture was completed separately.

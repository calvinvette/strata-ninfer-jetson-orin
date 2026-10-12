# Q2_0 graph control compatibility probe — Orin — 2026-10-12

Two candidate controls for the captured 64K-context Q2_0 serving graph were
checked with the existing supervised graph probe. Both stopped before the
health check/request, so neither produced a graph-memory comparison:

* `--no-capture` was rejected by Strata's native-route safety guard. The log
  explains that this path runs `session_token`, which lacks the CPU expert-pool
  hook and would silently omit routed experts unless switched to a separate
  GPU-only floor mode. That is not an equivalent serving control.
* `--no-token-graph` let the engine initialize, but the Python serving layer
  rejected the configuration before readiness with its required spec/prefill/
  expert-profile diagnostic. It is not a supported serving comparison on this
  candidate.

Both supervised attempts remained well above the six-GiB floor (minimum host
availability 21.29 GiB and 21.14 GiB, respectively); these were compatibility
failures, not memory-pressure failures. Raw commands, generated configs, engine
logs, and supervisor telemetry are retained in the sibling
`capture-mode-comparison/` and `graph-layout-comparison/` directories.

The control comparison is therefore unsupported for the current serving route.
The separate supported captured-path NVMap/context attribution remains valid
for its tested 32K/64K configuration, but these attempts add no uncaptured
baseline and do not close Phase 3 graph-backing ownership.

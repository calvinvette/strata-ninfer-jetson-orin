# Q2_0 stage backing: instrumented timing diagnostic

This seven-pair run completed with output-token parity, but is **excluded from
the timing conclusion**. Although the harness removed Strata trace flags in
timing-only mode, the config also supplied a CUDA graph-driver probe through
`LD_PRELOAD`; that preload remained active. The raw logs include
`GRAPH_DRIVER_MEM` events, so this was not an instrumentation-free timing run.

The experiment directory is retained without deleting or rewriting any raw
results. Its paired values are available in `summary.json` for audit only. The
clean rerun, with `LD_PRELOAD` removed by the timing-only environment, is
documented in
[`q2-stage-pin-confirm7-clean`](../2026-10-11-phase3-q2-stage-pin-confirm7-clean/README.md).

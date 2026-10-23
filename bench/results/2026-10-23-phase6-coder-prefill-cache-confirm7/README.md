# Coder prefill chunk × expert cache held-out confirmation

This confirmation follows the three-block screen in
[`2026-10-23-phase6-coder-prefill-cache-screen3`](../2026-10-23-phase6-coder-prefill-cache-screen3/README.md).
It reuses the IQ1_M model, 8K context, FP16 KV, MTP-off configuration and the
2 × 2 cache/chunk grid, but uses a different 7,501-token archive, different
marker locations and values, and a different arithmetic answer.

The confirmation has seven randomized blocks. Each block launches one fresh
service for each of the four cells, with one same-task warmup and one measured
request per cell. All cells use a 28-GiB cgroup limit and retain the six-GiB
physical host reserve. The analyzer audits the exact answer and prompt length,
cell completion, host reserve, cgroup scope and events, then computes paired
block contrasts and deterministic bootstrap intervals over blocks. Individual
tokens and repeated requests within a process are not treated as independent
replicates.

Model files remain in `~/models/strata-orin-validation/`. The exact prompt hash,
model revision, binary identity and campaign factors are in `design.json`.
Raw request and telemetry files are retained under `per-cell-scopes/` locally
and are not committed.

Run from the repository root:

```sh
python3 bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/run_confirm7.py
python3 bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/analyze_confirm7.py
```

To resume one unstarted block, pass `--block N` to the runner. The runner
refuses to overwrite an existing block directory. The analyzer defaults to
requiring all seven blocks; its optional `--blocks N` mode is for partial-data
audits and does not satisfy the confirmation gate.

## Status

The tokenizer check and a separate preflight passed. Both preflight requests
returned the exact answer at 7,501 prompt tokens; the natural-stop rule accepts
the model's 46-token response. The preflight retained over 14 GiB minimum host
availability, over 14 GiB admission availability, and zero cgroup events. It is
excluded from confirmation statistics. Block 1 is now running; no confirmation
performance result or configuration recommendation is yet available.

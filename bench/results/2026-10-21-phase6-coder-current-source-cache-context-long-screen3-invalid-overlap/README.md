# Coder cache × context long-prompt screen — Orin — 2026-10-21

This screen crosses requested expert-cache arguments 1,500/3,000 with configured
contexts 8K/16K on a held-out 7,501-token retrieval-and-arithmetic task. It
extends the short-prompt cache confirmation, which did not exercise the larger
context. The task uses the pinned Coder IQ1_M model and the exact answer from
the prepared workload. Each cell runs in a fresh Strata service with one
same-task warmup and one measured request. Three independent randomized blocks
are planned. This is screening evidence; one request per fresh cell does not
support confidence intervals or a setting recommendation.

## Identity and controls

- Hardware: Jetson AGX Orin, ARM64, CUDA 12, SM87.
- Model: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
  `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M two-shard GGUF. The model
  stays under `~/models/strata-orin-validation/Coder-GGUF/IQ1_M/`; hashes are
  recorded in `model-sha256.txt`.
- Source base commit: `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`; the compiled
  working tree includes current opt-in integration diagnostics. The exact
  executable hash is in `design.json`.
- Fixed settings: MTP off, FP16 KV, prefill 64, eight pool workers, prompt cache
  off, adaptive swaps off, mmap experts on, and read-only clock sampling.
- Only cache argument and configured context vary. Each service uses its own
  28-GiB cgroup scope, and the six-GiB physical host floor remains in force.
  No clocks are changed. Energy is not measured.

The prompt has three marker values at 10%, 50% and 90% of the 7,501-token
input. The exact answer is:

`EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, LATE=TIDAL-COPPER-529, SUM=1692`

## Execution

Reproduce with:

```sh
python3 bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-screen3/run_screen3.py
python3 bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-screen3/analyze_screen3.py
```

Each block randomizes the four cells independently. Results and supervisor
telemetry are retained under `per-cell-scopes/`. `analysis.json` reports exact
answer/token checks, actual cache allocation, physical host/admission floors,
cgroup events and descriptive paired effects. The three-block sample is not a
confirmation interval.

The screen is in progress. Do not pool the separately retained, aborted
seven-block preflight in `../2026-10-21-phase6-coder-current-source-cache-context-long-confirm7-aborted-preflight/`;
that attempt was stopped during its first cell after its projected runtime
proved disproportionate and yielded no complete measurement.

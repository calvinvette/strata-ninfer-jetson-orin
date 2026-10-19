# Current-source Q2_0 graph × MTP2 confirmation — Orin — 2026-10-19

This randomized seven-block confirmation repeats the task-qualified capture × MTP2 study using the current candidate binary. It uses the same validated 2,094-token processor explanation task, fresh service per cell, 512-token/one-token warmup, 8K context, FP16 KV, 3,000-slot expert cache, accepted-only adaptation cadence 4, eight workers, and 28-GiB service scope. The four conditions were captured/eager decode crossed with MTP off/window 2. Trace instrumentation was disabled. Each block randomized condition order.

All 28 cells passed. Every response used exactly 2,094 fresh prompt tokens, naturally stopped at 293 output tokens, passed the task rubric, and had byte-identical response text across all four conditions in each block and across the full campaign. MTP2 offered/accepted 153/97 drafts in every run. Minimum host/admission availability was 16.86/9.22 GiB. The 28-GiB cgroups recorded zero low/high/max/OOM/kill events.

| Contrast | Client request time, median paired change (95% interval) |
| --- | ---: |
| Captured vs eager, MTP off | +0.63% (-0.77% to +3.53%) |
| Captured vs eager, MTP2 | +1.43% (-3.23% to +3.88%) |
| MTP2 vs off, captured | +4.92% (-0.11% to +6.53%) |
| MTP2 vs off, eager | +4.77% (-1.91% to +6.41%) |
| Capture × MTP2 interaction | -2.48% (-4.66% to +6.85%) |

The request-time intervals include no change for all five contrasts. MTP2 reduced decode throughput by 5.00% (−8.54% to +2.63%) in captured mode and 5.06% (−7.32% to −3.70%) in eager mode. Its prompt-throughput penalty was about 3% in both modes, with intervals excluding no change. No serving profile is promoted from this one workload. Clocks were dynamic, and no process-attributed energy measurement was available.

This is a Q2_0 artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision `5348543e0147355ac9cbcb031184a3546350988e`. It is a same-repository quantization/runtime artifact check; it is not the Coder IQ1_M artifact referenced by the 2026-10-15 Phase 7 path. The service binary SHA256 is `b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa`; source HEAD at run time was `b6ea61888cb1ffb0bf92e79217d6a88d46178111`. Model, PLE, MTP and expert-profile hashes are in [`artifact-identities.json`](artifact-identities.json). Per-cell logs, requests, memory samples, clock telemetry and schedule are retained under [`run/`](run/).

Reproduce the campaign on Orin with:

```sh
python3 bench/results/2026-10-16-phase6-q2-graph-mtp-quality-confirm7/confirm7.py \
  --output bench/results/2026-10-19-phase6-q2-graph-mtp-current-source-confirm7/run \
  --blocks 7 --seed 202610194 --run
python3 bench/results/2026-10-19-phase6-q2-graph-mtp-current-source-confirm7/analyze_confirm7.py
python3 bench/results/2026-10-19-phase6-q2-graph-mtp-current-source-confirm7/plot_effects.py
```

The campaign script refuses to overwrite an existing output. Analysis uses seven whole-process paired ratios and 20,000 bootstrap resamples; tokens are not treated as independent replicates. This remains one artifact, task and runtime configuration. Phase 6 remains open for its other planned interactions and energy attribution; Phase 5 state and migration gates also remain open.

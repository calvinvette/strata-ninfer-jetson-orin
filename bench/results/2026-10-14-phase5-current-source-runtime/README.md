# Current-source accepted-prefix runtime check — Orin — 2026-10-14

This reruns the Q2_0 accepted-only MTP state comparison using the current
native CUDA/ARM64 binary after the accepted-window cap change. The executable
SHA256 is recorded in `binary-sha256.txt`; all model artifacts remain under
`~/models/strata-orin-validation/`.

The supervised run used the retained 2,048-token prompt
(`93cefb75fa4bb48eec0bcbf5771e06a6cce6bbad03c463df644fb45634b3dc15`), FP16
KV, 3,000 expert-cache slots, prefill 512, 8,192 context, 3-GiB workspace
reserve, CPU prefill sharing disabled, and a 32-token generation cap. Four
fresh services compared MTP off/2/3/4 with accepted-only adaptation every four
accepted tokens. All four generated token-ID sequences matched. All nine
persistent main-model state fields matched at final state and every common
accepted-prefix boundary: 22, 19 and 15 boundaries for MTP2/3/4. Drafts
offered/accepted were 17/10, 24/13 and 31/17.

The scope completed in 315.93 seconds under a 28-GiB cgroup cap. Minimum
physical host/admission availability was 16.88/8.38 GiB. Sampled `low`,
`high`, `max`, `oom` and `oom_kill` counters remained zero. This confirms the
tested prefix-state contract on the current binary and exact prompt; it does
not establish task quality, long-prompt correctness, same-service recovery
after adaptive swaps, or a performance effect. Timings are not used as a
comparison.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-current-source-runtime/supervisor \
  --timeout 7200 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-14-phase5-accepted-window-256/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-14-phase5-current-source-runtime/run \
  --prompt-tokens 2048 --tokens 32 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

Raw per-arm engine logs, the comparison JSON and supervised memory/clock
samples are retained beside this report. `SHA256SUMS.txt` verifies this
evidence.

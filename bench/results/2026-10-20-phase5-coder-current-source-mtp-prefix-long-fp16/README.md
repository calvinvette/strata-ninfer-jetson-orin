# Current-source Coder IQ1_M long-prompt MTP accepted-prefix check — FP16 KV — Orin — 2026-10-20

This Phase 5 correctness matrix crossed MTP off/windows 2, 3 and 4 with one
7,498-token Coder IQ1_M prompt, FP16 KV, 16 generated tokens, accepted-only
adaptive expert updates, and fresh services. It used current candidate binary
SHA256 `e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`
from checkout `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`, the pinned model
revision `5348543e0147355ac9cbcb031184a3546350988e`, and MTP runtime revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`. Full model and MTP artifact
SHA256 values are in [`artifact-sha256.txt`](artifact-sha256.txt); source-file
and executable SHA256 values are in [`source-identity-sha256.txt`](source-identity-sha256.txt).
Model artifacts stayed under `~/models/strata-orin-validation/`.

The independent accepted-prefix review passed for all arms. Windows 2/3/4
accepted 5/7, 7/10 and 8/13 drafts offered. Each produced exactly the MTP-off
16 token IDs and matched all nine persistent main-model state fingerprints at
final completion and every shared accepted-commit boundary: 11/11, 9/9 and 8/8
boundaries, respectively. Prompt token-ID SHA256 was
`50eb747cc4434346994883e56fcdd012802716623df56f0bdc4a5c65eb38acaa`.

The one measured request had prompt/decode engine times of 180.641/33.378 s
(MTP off), 181.290/24.989 s (window 2), 180.375/20.455 s (window 3), and
180.108/18.438 s (window 4). Arms were run sequentially rather than randomized
and replicated; these times and the apparent decode reduction are descriptive
only and are not a performance comparison or profile recommendation.

The 28-GiB supervisor passed in 891.3 s over 842 one-second samples. The
current integration unittest suite passed 163/163; focused accepted-window, GDN,
KV-format/stream and graph-lifecycle CTests passed 11/11. Minimum
host availability was 13.04 GiB and admission availability 11.34 GiB, above the
six-GiB floor. Scope `high`, `max`, `oom` and `oom_kill` event counters stayed
zero. CPU/GPU clocks were observed dynamically, EMC readback was denied and
energy was not attributed. Raw per-arm logs, the comparison record, supervisor
telemetry and clock observations are retained in `run/` and `supervisor/`.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/coder-mtp-long-fp16/supervisor \
  --timeout 2400 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/config.json \
  --engine build/integration/candidate/strata \
  --output /tmp/coder-mtp-long-fp16/run \
  --tokens 16 --prompt-tokens 7498 --kv-format fp16 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

This establishes accepted-prefix parity for this one long Coder/FP16 cell. It
does not cover other long prompts or KV formats, demonstrate a performance win,
or resolve the separate adaptive CPU/GPU migration state divergence. Phase 5
remains open.

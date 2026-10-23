# Current-source Coder IQ1_M long-prompt MTP accepted-prefix check — int8 KV — Orin — 2026-10-20

This Phase 5 correctness matrix crossed MTP off/windows 2, 3 and 4 with the
same 7,498-token Coder IQ1_M prompt used by the FP16-KV companion run, int8 KV,
16 generated tokens, accepted-only adaptive expert updates, and fresh services.
The prompt token-ID SHA256 is
`50eb747cc4434346994883e56fcdd012802716623df56f0bdc4a5c65eb38acaa`, matching
the FP16 run. Both use current candidate binary SHA256
`e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`, model
revision `5348543e0147355ac9cbcb031184a3546350988e`, and MTP runtime revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`. Model and runtime artifacts remain
under `~/models/strata-orin-validation/`. Their SHA256 values are in
[`artifact-sha256.txt`](artifact-sha256.txt); candidate and source hashes are
in [`source-identity-sha256.txt`](source-identity-sha256.txt).

The independent accepted-prefix review passed for all arms. Windows 2/3/4
accepted 5/7, 7/8 and 8/11 drafts offered. Each produced exactly the MTP-off
16 token IDs and matched all nine persistent main-model state fingerprints at
final completion and every shared accepted-commit boundary: 11/11, 9/9 and 8/8
boundaries, respectively.

The one measured request had prompt/decode engine times of 178.494/53.462 s
(MTP off), 180.649/39.651 s (window 2), 179.157/32.527 s (window 3), and
177.278/29.084 s (window 4). These were sequential one-shot arms rather than
randomized replicated blocks; times are descriptive only and do not estimate
an MTP or KV performance effect. Compare the separate [FP16-KV long-prompt
run](../2026-10-20-phase5-coder-current-source-mtp-prefix-long-fp16/README.md)
for its own state result, not as a paired timing control.

The 28-GiB supervisor passed in 946.8 s over 896 one-second samples. Minimum
host availability was 13.29 GiB and admission availability 12.00 GiB, above
the six-GiB floor. Scope `high`, `max`, `oom` and `oom_kill` event counters
stayed zero. CPU/GPU clocks were observed dynamically, EMC readback was denied
and energy was not attributed. Raw per-arm logs, accepted-prefix comparisons,
supervisor telemetry and clock observations are retained in `run/` and
`supervisor/`.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/coder-mtp-long-int8/supervisor \
  --timeout 2400 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/config.json \
  --engine build/integration/candidate/strata \
  --output /tmp/coder-mtp-long-int8/run \
  --tokens 16 --prompt-tokens 7498 --kv-format int8 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

This establishes accepted-prefix parity for one long Coder/int8-KV cell. It
does not cover other long prompts, demonstrate a performance win, or resolve
the separate adaptive CPU/GPU migration state divergence. Phase 5 remains open.

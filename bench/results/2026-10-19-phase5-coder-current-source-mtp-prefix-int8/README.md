# Current-source Coder IQ1_M MTP accepted-prefix check — int8 KV — Orin — 2026-10-19

This Phase 5 check extends the current-source Coder accepted-prefix run to
int8 KV. Four fresh services used the same exact 2,048-token prompt and
generated 16 tokens: MTP off as reference, then MTP windows 2, 3 and 4. The
independent review compared published token IDs, final persistent main-model
state, and state fingerprints at every shared accepted-prefix boundary.

All MTP windows matched the MTP-off arm's token IDs and all nine persistent
state fingerprints at completion and at every shared boundary. Windows 2, 3
and 4 offered/accepted 7/5, 10/7 and 13/8 drafts, with 11, 9 and 8 compared
boundaries. The exact prompt token-ID digest was
`93cefb75fa4bb48eec0bcbf5771e06a6cce6bbad03c463df644fb45634b3dc15`.

The candidate binary SHA256 is
`b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa`; its
engine source is commit `b6ea61888cb1ffb0bf92e79217d6a88d46178111`. The Coder
IQ1_M model is pinned to Hugging Face revision
`5348543e0147355ac9cbcb031184a3546350988e`. The MTP runtime is pinned to
`de4b8e4d43b917e7706784d8bb445c9af86a3540`. Model artifacts remained under
`~/models/strata-orin-validation/`; their hashes are recorded in
[`model-sha256.txt`](model-sha256.txt) and
[`mtp-runtime-sha256.txt`](mtp-runtime-sha256.txt).

The 28-GiB supervised scope completed in 396.8 seconds. Across 376 samples,
minimum host availability was 13.18 GiB and minimum admission availability was
10.10 GiB, above the six-GiB floor. Cgroup low/high/max/OOM/OOM-kill counters
were zero throughout. CPU/GPU clocks were observed dynamically; EMC readback
was denied and energy was not attributed. The independent result review is
[`verification.json`](verification.json); raw logs and telemetry are retained
in `run-2048/` and `supervisor-2048/`.

Reproduce on Orin from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-19-phase5-coder-current-source-mtp-prefix-int8/supervisor-2048 \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-19-phase5-coder-current-source-mtp-prefix-int8/run-2048 \
  --tokens 16 --prompt-tokens 2048 --kv-format int8 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

This confirms accepted-prefix parity for one current-source prompt/profile and
int8 KV. It does not establish quality or performance benefit, other workload
lengths or KV formats, or resolve the separate adaptive CPU/GPU migration
state divergence. Phase 5 remains open.

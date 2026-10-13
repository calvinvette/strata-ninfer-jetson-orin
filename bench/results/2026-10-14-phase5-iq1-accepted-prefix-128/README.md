# IQ1_M accepted-prefix MTP long-chain check — Orin — 2026-10-14

This correctness-only run extends accepted-prefix state evidence to the
Flash-Next IQ1_M model and a 128-token chain. Four fresh services generated 128
tokens from the same exactly 2,048-token incident prompt at 8K context, FP16 KV,
3,000 requested expert-cache slots, prefill chunk 64, zero CPU-prefill sharing,
and accepted-only adaptation every four published tokens. MTP windows were off,
2, 3 and 4. The MTP artifact is the local IQ1_M runtime pack under
`~/models/strata-orin-validation/`; model files were not copied into Git.

MTP windows 2/3/4 each matched all 128 published token IDs, final persistent
state and every one of their shared accepted-prefix state checkpoints against
MTP-off. There were 78, 74 and 58 shared checkpoint boundaries, respectively.
The MTP arms offered/accepted 66/50, 89/54 and 120/70 drafts. Checks use the
trace emitted after verifier commit completion; final text alone is not the
gate. This is one prompt, cache, context, KV format and opt-in adaptation
policy. It does not qualify default window-count adaptation, other models,
performance or task quality.

The six-GiB supervisor passed. Minimum host availability was 14,327,128,064
bytes (13.34 GiB); minimum effective admission headroom was 11,128,553,472
bytes (10.36 GiB). OOM counters remained zero. CPU/GPU clocks were observed but
not controlled; EMC access was denied and energy was not measured. Raw
per-service logs, accepted-prefix results, memory samples and tegrastats are
retained under `trace/` and `supervisor/`.

The command was:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-iq1-accepted-prefix-128/supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/compare_accepted_usage_windows.py \
  bench/results/2026-10-14-phase5-iq1-accepted-prefix-128/trace \
  bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/workloads.json \
  128 8192 \
  bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/baseline-mtp4-config.json \
  fp16 captured
```

Binary, harness and workload identities are in `SHA256SUMS.txt`.

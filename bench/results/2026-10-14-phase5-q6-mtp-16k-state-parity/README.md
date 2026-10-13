# IQ1_M 16K MTP accepted-prefix state parity

The 15,003-token 16K retrieval prompt passed a direct MTP-off versus MTP4
accepted-prefix comparison. Both arms generated the same 41 token IDs and the
same answer containing each of the three expected markers exactly once and in
order. The MTP4 arm offered 34 drafts and accepted 30. Every one of the 14
shared generated-prefix checkpoints (1, 4, 8, 12, 15, 16, 20, 21, 24, 28, 32,
36, 40, 41 tokens) matched in all nine persistent-state fields; final state
matched as well.

The IQ1_M Coder Q6_K warp-dequant profile used FP16 KV, 8 workers, accepted-only
adaptive swaps every four published tokens and a fixed requested expert cache
of 3,000 slots. The test used the same local artifacts and held-out three-marker
retrieval prompt as the Phase 7 16K request. Both direct trace arms reserved
16,384 context tokens. State tracing and MTP batch mode were enabled for the
comparison; those settings add overhead, so no performance result is claimed.
The MTP-off arm took about 13 minutes and the complete two-arm supervised
sequence about 25 minutes.

The 28-GiB supervisor passed with 13.01 GiB minimum host availability and
effective admission headroom, above the six-GiB floor. No OOM events or kills
were recorded. The complete accepted-prefix and final-state trace, both engine
logs, exact configs, source script, workload identity and telemetry are
retained in this directory. The IQ1_M model shard hashes are recorded in the
[related long-prefill record](../2026-10-14-phase5-q6-prefill-cancel-recovery/README.md).

This confirms one long-context task and one MTP4 profile. It does not establish
quality across prompts or formats, performance, graph interaction, or behavior
at other cache capacities and contexts. Phase 5 remains open.

Reproduce under the same supervisor settings with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output bench/results/2026-10-14-phase5-q6-mtp-16k-state-parity/supervisor \
    --timeout 2400 -- \
    python3 bench/results/2026-10-14-phase5-q6-mtp-recall-ablation/trace_recall_state.py \
      --mtp0-config bench/results/2026-10-14-phase5-q6-mtp-16k-state-parity/config-mtp0.json \
      --mtp4-config bench/results/2026-10-14-phase5-q6-mtp-16k-state-parity/config-mtp4.json \
      --workload bench/results/2026-10-14-phase7-q6-recall/workloads/workload-16384.json \
      --output bench/results/2026-10-14-phase5-q6-mtp-16k-state-parity/trace \
      --max-new 48
```

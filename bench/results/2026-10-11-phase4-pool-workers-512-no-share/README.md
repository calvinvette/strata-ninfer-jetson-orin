# CPU expert-pool worker correctness screen — Orin — 2026-10-11

This three-block randomized screen compared 1, 2, 4 and 8 CPU expert-pool
workers using the IQ1_M Coder model, Q2_0 MTP runtime, a 512-token prompt,
eight generated tokens and a fixed 3,903-slot expert cache. Each process first
ran a distinct 512-token warmup. CPU prefill sharing was disabled with
`STRATA_PREFILL_CPU_SHARE=0`; the measured request therefore isolates worker
count under that policy. All 12 measured requests passed, all reported the
same cache capacity, and their output hashes and full accepted-prefix state
traces matched. The run exercises the same prompt and decode path as the
previous state-drift diagnostics, but does not measure task quality.

The supervisor sampled minimum physical host availability of 14.06 GiB, above
the preserved 6 GiB floor. The engine SHA256 was
`3ed52e6e0f845415b8fb2f2c15577f4b90efe49be72e2866d0dc961dbb0c95b0`.

| Workers | Median prompt (ms) | Median decode (ms) | Median request (ms) |
| ---: | ---: | ---: | ---: |
| 1 | 18,056.0 | 4,497.7 | 22,553.7 |
| 2 | 17,804.5 | 4,090.7 | 21,895.2 |
| 4 | 17,748.5 | 3,813.5 | 21,562.0 |
| 8 | 17,526.7 | 3,665.9 | 21,189.9 |

The harness enables verbose tracing and accepted-prefix state hashing, which
adds synchronization and can change execution timing. These measurements are
correctness-screen timings only. Relative to eight workers, the paired request
time deltas were +5.86%, +6.14% and +6.86% for 1 worker; +2.64%, +3.74% and
+4.21% for 2; and +0.76%, +2.16% and +2.80% for 4. With only three blocks,
the displayed bootstrap intervals are not useful confirmation intervals.
No worker-count speedup is qualified and no default is changed. A timing-only
screen without tracing and a held-out workload belongs in the later paired
confirmation campaign.

The experiment kept request streams, server and engine logs, warmup workload,
accepted-prefix traces, memory samples and raw tegrastats in this directory.
Run under the repository's integration venv with `tools/integration/run_control.py`
and `tools/integration/pool_worker_screen.py`; the command and complete raw
results are recorded in `supervisor/result.json` and `experiment/results.json`.

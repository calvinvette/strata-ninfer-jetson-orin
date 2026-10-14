# Q2_0 32K retrieval plus arithmetic check — Orin — 2026-10-14

This Phase 7 cross-model check applied the existing long-context retrieval-plus-
arithmetic task to the Q2_0 accepted-only MTP4 profile at 32,768 configured
context. The prompt contained exactly 30,040 formatted tokens and placed three
independent codes near 10%, 50% and 90%. The 48-token answer returned each code
exactly once and in order, and gave the independently verified suffix sum:

```text
EARLY=MAPLE-ORBIT-731, MIDDLE=COBALT-HARBOR-284, LATE=VELVET-COPPER-956, SUM=1971
```

The oracle in `review_arithmetic.py` extracts the three suffixes, sums them
independently (`731 + 284 + 956 = 1971`), checks exact code counts and order,
and verifies that the same service returned `RECOVERED`. All checks passed.
The API harness's marker and recovery checks also passed.

The run used a 28-GiB cgroup ceiling and six-GiB physical-availability floor.
Minimum host availability was 16.292 GiB and minimum effective admission
availability was 10.274 GiB. Sampled cgroup `low`, `high`, `max`, `oom` and
`oom_kill` counters stayed at zero. It took 644.79 seconds including startup,
warmup, retrieval and recovery. The retrieval request took 574.11 seconds;
engine telemetry reported 564.64 seconds prefill and 9.42 seconds decoding at
5.1 tokens/second. Twenty-four of 24 draft tokens were accepted. No prompt
tokens were cached. Clocks were observed without control; EMC frequency access
was denied, and energy was not process-attributed.

Two setup attempts are retained and excluded: the copied driver initially
resolved the wrong repository root and failed to import `tools` before server
startup. The corrected retry used the repository root explicitly, passed its
CLI import check, and completed the test. No model request ran during either
failed setup attempt.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/supervisor-retry2 \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/run_quality_task.py \
  --config bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/config.json \
  --workload bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/workload.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/warmup-512.json \
  --output bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/run-retry

python3 bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/review_arithmetic.py \
  bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/run-retry/result.json
```

Raw outputs for both failed setup attempts and the successful run are retained
in this directory. The parent `SHA256SUMS.txt` records checksums.

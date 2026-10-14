# Q2_0 32K near-limit retrieval and recovery — Orin — 2026-10-14

This follow-up used the same accepted-only MTP4 configuration as the 8K and
16K checks, with a 32,768-token context and a newly prepared 30,032-token
prompt. All three codes near 10%, 50% and 90% were returned exactly once and
in order in 41 completion tokens. The same service returned `RECOVERED` after
the retrieval request.

The run passed under the 28-GiB cgroup ceiling and six-GiB physical-availability
guard. Minimum host availability was 16.363 GiB and minimum effective admission
availability was 10.307 GiB. Sampled cgroup `low`, `high`, `max`, `oom` and
`oom_kill` counters stayed at zero. Clocks were observed without control; EMC
frequency access was denied. Energy was not process-attributed.

The retrieval request took 582.38 seconds end to end; engine telemetry reported
574.48 seconds prefill and 7.85 seconds decoding at 5.2 tokens/second. This is
one workload observation, not a paired performance result. The exact config,
prompt, API response, engine log, and supervisor telemetry are retained in this
directory. `SHA256SUMS.txt` covers the run files.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/supervisor-32768 \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/run_recall_case.py \
  --config bench/results/2026-10-14-phase7-q2-recall/config-32768-mtp4.json \
  --workload bench/results/2026-10-14-phase7-q2-recall/workloads-32768/workload-32768.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output bench/results/2026-10-14-phase7-q2-recall/run-32768
```

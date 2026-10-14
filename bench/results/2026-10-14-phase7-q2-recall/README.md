# Q2_0 near-limit retrieval and recovery — Orin — 2026-10-14

These Phase 7 checks add long-context task evidence for the Q2_0 native model.
Fresh services used the accepted-only MTP configuration, 3,000 requested
expert-cache slots, FP16 KV, a 3-GiB workspace reserve and 8,192- or
16,384- or 32,768-token configured contexts. The model shards and runtime MTP
pack stayed under `~/models/strata-orin-validation/`; the runtime binary SHA256
is recorded in `SHA256SUMS.txt`. The Q2_0 source files were
`Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` (37,623,740,192 bytes)
and `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` (28,800,138,432
bytes), with the prepared native pack described by the local `conversions.json`.
The runtime config records exact local paths and flags.

The exact formatted retrieval prompts contained 7,498, 15,003 and 30,032
tokens. At all three lengths, independent codes placed near 10%, 50% and 90%
were returned exactly once and in order in 41-token answers. A separate
512-token warmup completed first, and each service then returned `RECOVERED`
on a short request. This checks retrieval and recovery for these prompts and
this profile; it does not qualify other tasks, MTP settings, or general model
quality. Individual 16K and 32K run details are in
[README-16384.md](README-16384.md) and [README-32768.md](README-32768.md).

A separate 30,040-token [32K retrieval-plus-arithmetic replication](quality-replication-32768/README.md)
also returned the three codes in order and the independently checked suffix
sum `1971`, then passed same-service recovery. This is a single task-quality
check for the Q2_0 cohort, not a broad quality score.

All three runs passed under a 28-GiB cgroup ceiling and the six-GiB
host-availability guard. Minimum physical host availability was 16.967, 16.797
and 16.363 GiB at 8K, 16K and 32K; minimum effective admission availability
was 10.146, 10.355 and 10.307 GiB. Sampled cgroup `low`, `high`, `max`, `oom`
and `oom_kill` counters stayed at zero. CPU and GPU clocks were observed
without control; EMC frequency access was denied. Energy was not process-
attributed.

Retrieval took 146.59, 261.45 and 582.38 seconds end to end at 8K, 16K and
32K. Engine telemetry reported 139.06, 253.59 and 574.48 seconds prefill and
7.52, 7.83 and 7.85 seconds decoding at 5.5, 5.2 and 5.2 tokens/second.
These are single-run workload observations, not a paired performance
comparison. All runs used no prompt-cache reuse and stopped at 41 tokens within
a 48-token allowance.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/run_recall_case.py \
  --config bench/results/2026-10-14-phase7-q2-recall/config-8192-mtp4.json \
  --workload bench/results/2026-10-14-phase7-q2-recall/workloads/workload-8192.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output bench/results/2026-10-14-phase7-q2-recall/run
```

Raw API results, engine output, supervisor samples and clock observations are
retained alongside both configs and workloads. The reusable workload
preparation script is included; it uses the local tokenizer and exact prepared
prompt hashes are listed in `SHA256SUMS.txt`.

# Q2_0 near-limit retrieval and recovery — Orin — 2026-10-14

This Phase 7 check adds long-context task evidence for the Q2_0 native model.
One fresh service used the accepted-only MTP configuration, 3,000 requested
expert-cache slots, FP16 KV, a 3-GiB workspace reserve and an 8,192-token
configured context. The model shards and runtime MTP pack stayed under
`~/models/strata-orin-validation/`; the runtime binary SHA256 is recorded in
`SHA256SUMS.txt`. The Q2_0 source files were
`Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` (37,623,740,192 bytes)
and `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` (28,800,138,432
bytes), with the prepared native pack described by the local `conversions.json`.
The runtime config records exact local paths and flags.

The exact formatted retrieval prompt contained 7,498 tokens. Three independent
codes placed near 10%, 50% and 90% were returned exactly once and in order in a
41-token answer. A separate 512-token warmup completed first. The same service
then returned `RECOVERED` on a short request. This checks retrieval and recovery
for this prompt and profile; it does not qualify other contexts, tasks, MTP
settings, or general model quality.

The run passed under a 28-GiB cgroup ceiling and the six-GiB host-availability
guard. Minimum physical host availability was 16.967 GiB and minimum effective
admission availability was 10.146 GiB. Sampled cgroup `low`, `high`, `max`,
`oom` and `oom_kill` counters stayed at zero. CPU and GPU clocks were observed
without control; EMC frequency access was denied. Energy was not process-
attributed.

The retrieval request took 146.59 seconds end to end; the engine reported
139.06 seconds prefill and 7.52 seconds decoding at 5.5 tokens/second. These
are single-run workload observations, not a paired performance comparison.
The run used no prompt-cache reuse. The exact workload has 7,498 prompt tokens
and a 48-token allowance; the answer stopped at 41 tokens.

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
retained alongside the config and workloads. The reusable workload preparation
script is included; it uses the local tokenizer and the exact prepared prompt
hash is listed in `SHA256SUMS.txt`.

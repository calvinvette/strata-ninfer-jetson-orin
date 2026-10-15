# Q2_0 128K near-limit retrieval and recovery — Orin — 2026-10-15

This extends the Q2_0 capacity ladder from 65,536 to 131,072 configured
context tokens. A fresh service used the accepted-only MTP4 profile, 3,000
requested expert-cache slots, FP16 KV, a 3-GiB workspace reserve and eight
workers. Model and pack files remained in `~/models/strata-orin-validation/`.

The formatted near-limit prompt contained 120,149 tokens. The service returned
the three independent markers at 10%, 50% and 90% exactly once and in order in
a 41-token answer, then returned `RECOVERED` to a short same-service request.
A separate 512-token warmup preceded retrieval. This qualifies one Q2_0 task
and profile at 128K; it does not establish broad task quality or a general
capacity boundary.

The supervised run took 5,604.9 seconds including startup and warmup; retrieval
took 5,546.4 seconds at 21.7 prompt tokens/second. Minimum physical host
availability was 13.651 GiB and minimum effective admission availability was
13.194 GiB, above the six-GiB host floor. Across 5,344 one-second memory
samples, cgroup `low`, `high`, `max`, `oom` and `oom_kill` event counts stayed
at zero. GPU clocks varied from 306 MHz to 1,300.5 MHz; no clocks were set.
EMC readback was denied, and energy was not request-attributed. These are
single-run capacity observations, not a paired performance comparison.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-q2-recall-128k/supervisor \
  --timeout 10800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/run_recall_case.py \
  --config bench/results/2026-10-15-phase7-q2-recall-128k/config-131072-mtp4.json \
  --workload bench/results/2026-10-15-phase7-q2-recall-128k/workloads/workload-131072.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output bench/results/2026-10-15-phase7-q2-recall-128k/run
```

The exact prompt, config, engine output, result, binary identity and telemetry
are retained here. Model files were not copied into Git.

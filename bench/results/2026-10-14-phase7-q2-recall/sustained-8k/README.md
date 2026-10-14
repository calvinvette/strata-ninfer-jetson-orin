# Q2_0 sustained 8K retrieval and service check — Orin — 2026-10-14

This Phase 7 run sustained the Q2_0 accepted-only MTP4 profile for 30 minutes
after a 7,498-token retrieval precondition. It used an 8,192-token configured
context, 3,000 requested expert-cache slots, FP16 KV, a 3-GiB workspace reserve,
and `--prompt-cache 0`. Each repeated request therefore read the full prompt;
this checks serial fresh-prefill service stability, not cache-reuse performance.

The measured loop lasted 1,823.13 seconds and completed 14 retrieval requests
with zero failures. Every request used exactly 7,498 prompt tokens and returned
the three expected markers exactly once and in order. The precondition also
passed. `review_sustained.py` independently checks every retained request row.
No prompt tokens were cached.

The 28-GiB supervisor retained 16.971 GiB minimum physical host availability
and 9.546 GiB minimum effective admission availability. Sampled cgroup `low`,
`high`, `max`, `oom` and `oom_kill` counters stayed at zero. The tegrastats
`tj` sensor ranged from 54.5 to 60.1 °C during the loop; the first and last
five-minute means were 55.3 and 56.0 °C. This supports thermal stability for
this workload and session. CPU/GPU clocks were observed without control; EMC
frequency access was denied, and energy was not process-attributed.

Median repeated-request latency was 128.27 seconds and median first-visible
token time was 124.69 seconds. These are descriptive single-run measurements
under dynamic clocks, not a paired performance comparison. The full prompt is
reprocessed on each request.

The first harness attempt is retained in `supervisor/`; it failed before
service startup because a copied script resolved the wrong import path. The
corrected run is in `supervisor-retry/` and `run/`. No model request ran in the
failed attempt.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-8k/supervisor-retry \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/sustained-8k/run_sustained.py \
  --config bench/results/2026-10-14-phase7-q2-recall/sustained-8k/config.json \
  --workload bench/results/2026-10-14-phase7-q2-recall/workloads/workload-8192.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-8k/run \
  --duration-seconds 1800

python3 bench/results/2026-10-14-phase7-q2-recall/sustained-8k/review_sustained.py \
  --result bench/results/2026-10-14-phase7-q2-recall/sustained-8k/run/result.json \
  --requests bench/results/2026-10-14-phase7-q2-recall/sustained-8k/run/requests.jsonl \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-8k/quality-review.json
```

The exact request rows, service log, supervisor samples, clock observations
and checksums are retained in this directory and the parent `SHA256SUMS.txt`.

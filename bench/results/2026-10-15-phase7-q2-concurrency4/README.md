# Q2_0 four-slot API concurrency screen — Orin — 2026-10-15

This screen submitted four distinct 7,498-token Q2_0 retrieval prompts to one
streaming API service configured with four batch slots. Each answer returned
its own three planted codes exactly once and in order, with the exact prompt
count; all four request-level retrieval checks passed. The server reported four
serving slots and four running requests at peak. However, `/metrics` showed at
most two non-idle slot states during 1-second supervisor sampling. The runner's
four-way overlap gate therefore failed. This does not qualify four-way active
serving; the earlier two-slot result remains the only bounded concurrency
qualification.

The service used the Q2_0 accepted-only MTP4 configuration with swaps disabled,
16,384 configured context, FP16 KV, 3,000 expert-cache slots, a 3 GiB VRAM
reserve and eight pool workers. The Orin binary SHA-256 was
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`. The
28-GiB supervised run lasted 1,352.6 seconds over 1,286 one-second samples.
Minimum host/admission availability was 14.65/11.95 GiB. Sampled cgroup
`low`, `high`, `max`, `oom` and `oom_kill` counters all remained zero. Observed
GPU clocks ranged from 306 MHz to 1,300.5 MHz; no clocks were changed. Energy
was not request-attributed and EMC frequency readback was unavailable.

All four requests completed; observed request durations were 858, 1,082, 592
and 1,301 seconds. The runner exited 1 because its four-active-slot gate did not
pass, not because of retrieval errors or a memory-floor failure. Its result
file and the failed qualification state are retained. Per-second memory
samples are gzip-compressed at `supervisor/memory.jsonl.gz`. Workload/config
identities and all retained file digests are in `SHA256SUMS.txt`.

The screen bounds the current evidence: four slots can be configured and all
four retrieval requests can complete with correct answers, while the sampled
server metric exposed no more than two active slots. Phase 7 remains open; do
not describe this as four-way support or a throughput improvement.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-q2-concurrency4/supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-15-phase7-q2-concurrency4/run_concurrency4.py \
  --config bench/results/2026-10-15-phase7-q2-concurrency4/config.json \
  --warmup bench/results/2026-10-15-phase7-q2-concurrency4/warmup-512.json \
  --workloads bench/results/2026-10-15-phase7-q2-concurrency4/workloads/workload-1.json \
    bench/results/2026-10-15-phase7-q2-concurrency4/workloads/workload-2.json \
    bench/results/2026-10-15-phase7-q2-concurrency4/workloads/workload-3.json \
    bench/results/2026-10-15-phase7-q2-concurrency4/workloads/workload-4.json \
  --output bench/results/2026-10-15-phase7-q2-concurrency4/run
```

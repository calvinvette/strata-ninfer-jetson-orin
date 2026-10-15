# Q2_0 sustained prompt-cache reuse — Orin — 2026-10-14

This Phase 7 run adds a 30-minute cache-reuse stream for the Q2_0
accepted-only MTP4 profile. It used an 8,192-token configured context, the
exact 7,498-token retrieval prompt, FP16 KV, 3,000 requested expert-cache
slots, a 3-GiB workspace reserve, eight pool workers, and `--prompt-cache 6`.
The cache setting retained and reused the shared prompt prefix; it is distinct
from the separate conversation snapshot cache, which remained at zero MiB.

After a cold retrieval precondition, the measured interval was 1,800.19 seconds.
It completed 653 streamed requests with no request failures. An independent
review checked each completion for the three expected markers exactly once and
in order. Every request read exactly 7,498 prompt tokens, returned 41 tokens,
and reported exactly 7,491 reused tokens (`cache_n` and cached-prompt usage).
The median request time was 2.86 seconds, p95 was 2.90 seconds, and median
time to first visible token was 0.390 seconds. These figures describe this
cache-reuse prompt and profile; they are not fresh-prefill throughput.

The run used a 28-GiB cgroup ceiling and the six-GiB physical-availability
abort floor. Minimum host availability was 16.93 GiB, minimum admission
availability 10.72 GiB, and peak measured scope use 17.28 GiB. Sampled cgroup
`high`, `max`, `oom`, and `oom_kill` events remained zero. Tegrastats `tj`
spanned 48.6–68.7 °C, with a last-ten-minute mean of 67.7 °C. CPU/GPU clocks
remained under dynamic policy; sampled GPU frequency ranged from 306 to
1,300.5 MHz. EMC frequency access was denied, and energy was not attributed to
the request process.

The service binary SHA256 is
`e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`; the
configuration SHA256 is
`f1ca9dc298d7c87c72f698ca7b9addcb1ff9bec7cbef9192ad874ae2028ebf44`, and the
workload SHA256 is
`566fa526c26a7306c600a627e1726b3fc8c9477c87aab869566ce458d8d01f5b`.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/run_cache_reuse.py \
  --config bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/config.json \
  --workload bench/results/2026-10-14-phase7-q2-recall/workloads/workload-8192.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/run \
  --duration-seconds 1800

python3 bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/review_cache_reuse.py \
  --result bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/run/result.json \
  --requests bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/run/requests.jsonl \
  --output bench/results/2026-10-14-phase7-q2-recall/cache-reuse-30m/quality-review.json
```

Raw request rows, server output, supervisor memory samples, clock observations,
and tegrastats are retained here. The result covers one Q2_0 prompt/profile and
does not qualify other contexts, tasks, models, or defaults.

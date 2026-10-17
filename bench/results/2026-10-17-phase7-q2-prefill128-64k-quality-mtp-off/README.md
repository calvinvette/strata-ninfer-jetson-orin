# Q2_0 selected-profile 64K retrieval, arithmetic and recovery — Orin — 2026-10-17

The selected Q2_0 MTP-off profile passed one 64K retrieval-plus-arithmetic
quality task and same-service recovery. The actual uncached prompt was 60,079
tokens. The 48-token answer returned three planted codes exactly once and in
order and reported `SUM=1971`. An independent oracle extracted suffixes 731,
284 and 956 and computed 1,971; the same service then returned `RECOVERED`.
A second review checked prompt length, configured context, runtime settings,
uncached status, markers, recovery, memory guard and cgroup events.

The run used the selected profile: Q2_0 GGUF, FP16 KV, MTP off (`--spec 2`, no
MTP model), 65,536 context, 3,000 exact expert slots (3,955 MiB), prefill chunk
128, eight workers, prompt cache and adaptive swaps disabled, and a 3,072-MiB
workspace reserve. The workload is the already validated Q2_0 64K arithmetic
task previously run under MTP4. This is a profile-specific replication of that
task, not a new held-out prompt. The model was the
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. Model, pack, tokenizer and profile
files remained under `~/models/strata-orin-validation/`; model shard hashes
are recorded in the [prior selected-profile report](../2026-10-17-phase7-q2-prefill128-64k-selected-profile/artifacts.json).

The run used a 28-GiB cgroup limit and six-GiB host/admission guard. Minimum
host availability was 16.71 GiB and minimum effective-admission availability
was 10.74 GiB across 2,224 one-second samples. Peak cgroup use was 17.26 GiB;
`low`, `high`, `max`, `oom` and `oom_kill` events were all zero. Sampled CPU
clocks ranged from 729.6 to 2,201.6 MHz, GPU clocks from 306 to 1,300.5 MHz,
and `tj` from 50.031 to 56.937 °C. EMC readback was denied. No clock controls
were applied. Raw rail telemetry is retained but is not process-attributed
energy.

Engine-reported prefill took 2,283.6 seconds at 26.3 tokens/s; the client
request took 2,293.3 seconds, including 9.7 seconds to generate 48 tokens at
4.9 tokens/s. Same-service recovery took 4.0 seconds. These measurements cover
one prompt/profile cell and do not establish broad 64K quality, a performance
comparison or general support. The arithmetic and runtime reviews, raw answer,
engine/service logs, memory/clock samples and `tegrastats` are retained here.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-prefill128-64k-quality-supervisor --timeout 5400 \
  --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-15-phase7-q2-quality-64k/run_quality_task.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128-64k-quality-mtp-off/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-64k-quality-mtp-off/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128-64k-quality-mtp-off/warmup-workload.json \
  --output /tmp/q2-prefill128-64k-quality-run

python3 bench/results/2026-10-15-phase7-q2-quality-64k/review_arithmetic.py \
  /tmp/q2-prefill128-64k-quality-run/result.json

python3 bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/review_capacity.py \
  --result /tmp/q2-prefill128-64k-quality-run/result.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-64k-quality-mtp-off/workload.json \
  --supervisor /tmp/q2-prefill128-64k-quality-supervisor/result.json \
  --memory /tmp/q2-prefill128-64k-quality-supervisor/memory.jsonl \
  --context 65536 --output /tmp/q2-prefill128-64k-quality-run/independent-review.json
```

Both reviewers passed and the service exited cleanly; port 18888 closed. This
adds one selected-profile 64K quality point and does not close Phase 7.

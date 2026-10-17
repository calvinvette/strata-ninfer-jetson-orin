# Q2_0 selected-profile 32K retrieval, arithmetic and recovery — Orin — 2026-10-17

The selected Q2_0 MTP-off profile passed one held-out 32K retrieval-plus-
arithmetic quality task and same-service recovery. The actual uncached prompt
was 30,040 tokens. The 48-token answer returned three independently planted
codes exactly once and in order, and reported `SUM=1971`. The independent
arithmetic oracle extracted the suffixes 731, 284 and 956, summed them to 1971,
and verified that the same service returned `RECOVERED`. A second review
checked prompt length, configured context, runtime settings, uncached status,
markers, recovery, memory guard and cgroup events.

The configuration matched the selected profile: Q2_0 GGUF, FP16 KV, MTP off
(`--spec 2`, no MTP model), 32,768 context, 3,000 exact expert slots (3,955
MiB), prefill chunk 128, eight workers, prompt cache disabled, adaptive swaps
disabled and a 3,072-MiB workspace reserve. The workload is the previously
validated held-out 32K retrieval-and-arithmetic task, now run under the selected
MTP-off profile. The model was the
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. Model, pack, tokenizer and profile
files remained under `~/models/strata-orin-validation/`. Full hashes are in
[`artifacts.json`](artifacts.json); source and binary identity are in
[`source-revision.txt`](source-revision.txt).

The run used a 28-GiB cgroup limit and six-GiB host/admission guard. Minimum
host availability was 17.42 GiB and minimum effective-admission availability
was 11.48 GiB across 1,081 one-second samples. The cgroup peaked at 16.52 GiB,
with zero `low`, `high`, `max`, `oom` and `oom_kill` events. Sampled CPU clocks
ranged from 729.6 to 2,201.6 MHz, GPU clocks from 306 to 1,300.5 MHz, and `tj`
from 49.75 to 57.062 °C; EMC clock readback was denied. No clock controls were
applied. Raw rail telemetry is retained and is not process-attributed energy.

Engine-reported prefill took 1,085.3 seconds at 27.7 tokens/s. The retrieval
request took 1,095.0 seconds, including 9.7 seconds to generate 48 tokens at
5.0 tokens/s; same-service recovery took 4.3 seconds. These observations apply
to this single task/profile cell. They do not establish broad 32K model quality,
a performance comparison or general support. Both independent reviews and the
raw requests, service logs, memory/clock samples and `tegrastats` are retained
here.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-prefill128-32k-quality-supervisor --timeout 3600 \
  --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/quality-replication-32768/run_quality_task.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128-32k-quality-mtp-off/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-32k-quality-mtp-off/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128-32k-quality-mtp-off/warmup-workload.json \
  --output /tmp/q2-prefill128-32k-quality-run

python3 bench/results/2026-10-17-phase7-q2-prefill128-32k-quality-mtp-off/review_arithmetic.py \
  /tmp/q2-prefill128-32k-quality-run/result.json
```

The `run_quality_task.py` harness and arithmetic reviewer were inherited from
the earlier MTP4 study; the complete command and exact inputs above reproduce
the MTP-off configuration measured here. The shared capacity reviewer is at
[`review_capacity.py`](../2026-10-17-phase7-q2-prefill128-16k-selected-profile/review_capacity.py)
and independently passed for this result.

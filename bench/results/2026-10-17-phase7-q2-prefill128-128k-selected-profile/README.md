# Q2_0 selected-profile 128K capacity, retrieval and recovery — Orin — 2026-10-17

The selected Phase 6 Q2_0 MTP-off profile passed one near-limit retrieval and
same-service recovery cell at 128K configured context. The actual uncached
prompt was 120,149 tokens; all three planted codes appeared exactly once and in
order, the model generated 41 tokens, and the same service then returned
`RECOVERED`. The independent review checked context and runtime profile, exact
prompt count, uncached status, marker positions, recovery, supervisor headroom,
28-GiB scope and cgroup event counters.

The configuration matched the selected profile except for the tested context:
Q2_0 GGUF, FP16 KV, MTP off (`--spec 2`, no MTP model), 131,072 context, 3,000
exact expert slots (3,955 MiB), prefill chunk 128, eight workers, prompt cache
disabled, adaptive swaps disabled and a 3,072-MiB workspace reserve. The model
was the `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. Its shard hashes match the pinned
hashes already recorded in the [64K selected-profile report](../2026-10-17-phase7-q2-prefill128-64k-selected-profile/artifacts.json).
Model, pack, tokenizer and profile files remained under
`~/models/strata-orin-validation/`; full run provenance is in
[`artifacts.json`](artifacts.json).

The run used a 28-GiB cgroup limit and six-GiB host/admission guard. Minimum
host availability was 15.02 GiB and minimum effective-admission availability
was 11.73 GiB across 5,092 one-second memory samples. Peak cgroup use was
16.27 GiB; `low`, `high`, `max`, `oom` and `oom_kill` events were all zero.
Sampled CPU clocks ranged from 729.6 to 2,201.6 MHz, GPU clocks from 306 to
1,300.5 MHz, and `tj` from 49.375 to 56.968 °C. EMC readback was denied. No
clock controls were applied. Raw rail telemetry is retained but is not
process-attributed energy.

Engine-reported prefill took 5,302.2 seconds at 22.7 tokens/s. The client
retrieval request took 5,311.3 seconds, including 9.0 seconds for 41 generated
tokens; same-service recovery took 4.4 seconds. These observations describe
one prompt/profile cell, not a performance comparison or broad 128K support
claim. The independent review, request output, engine log, supervisor samples
and raw `tegrastats` are retained here.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-prefill128-128k-supervisor --timeout 12000 --interval 1 \
  --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-q2-prefill128/run_recall_case.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128-128k-selected-profile/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-128k-selected-profile/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128-128k-selected-profile/warmup-workload.json \
  --output /tmp/q2-prefill128-128k-run

python3 bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/review_capacity.py \
  --result /tmp/q2-prefill128-128k-run/result.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-128k-selected-profile/workload.json \
  --supervisor /tmp/q2-prefill128-128k-supervisor/result.json \
  --memory /tmp/q2-prefill128-128k-supervisor/memory.jsonl \
  --context 131072 --output /tmp/q2-prefill128-128k-run/independent-review.json
```

The service exited and port 18890 closed after the run. The selected profile
now has individual capacity cells from 8K through 128K; these do not establish
broad context support. Phase 7 remains open.

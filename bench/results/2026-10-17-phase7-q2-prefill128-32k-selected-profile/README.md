# Q2_0 selected-profile 32K capacity, retrieval and recovery — Orin — 2026-10-17

The selected Phase 6 Q2_0 MTP-off profile passed one near-limit retrieval and
same-service recovery cell at 32K configured context. The actual uncached prompt
was 30,032 tokens; all three planted codes appeared exactly once and in order,
the model generated 41 tokens, and the same service then returned `RECOVERED`.
The independent review checked the configured context and runtime profile,
exact prompt count, uncached status, marker positions, recovery answer,
supervisor headroom, 28-GiB scope and cgroup memory-event counters.

The configuration matched the selected profile except for the tested context:
Q2_0 GGUF, FP16 KV, MTP off (`--spec 2`, no MTP model), 32,768 context, 3,000
exact expert slots (3,955 MiB), prefill chunk 128, eight workers, prompt cache
disabled, adaptive swaps disabled and a 3,072-MiB workspace reserve. The model
was the `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. All model, pack, tokenizer and
profile files remained under `~/models/strata-orin-validation/`. Full hashes
are in [`artifacts.json`](artifacts.json), with source and binary identity in
[`source-revision.txt`](source-revision.txt).

The run used a 28-GiB cgroup limit and six-GiB host/admission guard. Minimum
host availability was 17.52 GiB and minimum effective-admission availability
was 11.89 GiB across 1,106 one-second memory samples. The cgroup peaked at
16.11 GiB, with zero `low`, `high`, `max`, `oom` and `oom_kill` events. Sampled
CPU clocks ranged from 729.6 to 2,201.6 MHz, GPU clocks from 306 to 1,300.5 MHz,
and `tj` from 49.437 to 56.625 °C; EMC clock readback was denied. No clock
controls were applied. Raw rail telemetry is retained and is not
process-attributed energy.

Engine-reported prompt processing took 1,112.8 seconds at 27.0 tokens/s. The
retrieval request took 1,121.3 seconds, including 8.4 seconds for 41 generated
tokens; same-service recovery took 4.0 seconds. These observations describe one
prompt/profile cell and are not a performance comparison or broad 32K support
claim. The independent review is in `run/independent-review.json`; raw request
and service logs, supervisor memory/clock samples and `tegrastats` are retained.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-prefill128-32k-supervisor --timeout 3600 --interval 1 \
  --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-q2-prefill128/run_recall_case.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128-32k-selected-profile/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-32k-selected-profile/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128-32k-selected-profile/warmup-workload.json \
  --output /tmp/q2-prefill128-32k-run

python3 bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/review_capacity.py \
  --result /tmp/q2-prefill128-32k-run/result.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-32k-selected-profile/workload.json \
  --supervisor /tmp/q2-prefill128-32k-supervisor/result.json \
  --memory /tmp/q2-prefill128-32k-supervisor/memory.jsonl \
  --context 32768 --output /tmp/q2-prefill128-32k-run/independent-review.json
```

The service exited and port 18885 closed after the run. The independent
reviewer passed `py_compile` and was validated against the selected-profile 8K
and 16K cells. The Phase 7 matrix contains the corresponding bounded result.

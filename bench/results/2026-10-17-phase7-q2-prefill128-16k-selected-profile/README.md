# Q2_0 selected-profile 16K capacity, retrieval and recovery — Orin — 2026-10-17

The selected Phase 6 Q2_0 MTP-off profile passed one near-limit retrieval and
same-service recovery cell at 16K configured context. The actual uncached prompt
was 15,003 tokens; the model returned the three codes planted near 10%, 50% and
90% of the prompt exactly once and in order, generated 41 tokens, and then
returned `RECOVERED` on the same service. Independent review checked the prompt
count, runtime context and profile, marker positions, recovery response,
supervisor floor, 28-GiB scope and memory-event counters.

The configuration matched the selected profile except for the tested context:
Q2_0 GGUF, FP16 KV, MTP off (`--spec 2`, no MTP model), 16,384 context, 3,000
exact expert slots (3,955 MiB), prefill chunk 128, eight workers, prompt cache
disabled, adaptive swaps disabled and a 3,072-MiB workspace reserve. The model
was the `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. Model, pack, tokenizer and profile
files remained under `~/models/strata-orin-validation/`. See
[`artifacts.json`](artifacts.json) for full hashes and
[`source-revision.txt`](source-revision.txt) for source/binary identity.

Under a 28-GiB cgroup limit and the six-GiB host/admission guard, minimum host
availability was 17.72 GiB and minimum effective-admission availability was
10.15 GiB across 611 one-second supervisor samples. The cgroup peaked at 17.85
GiB, with zero `low`, `high`, `max`, `oom` and `oom_kill` events. Sampled CPU
clocks ranged from 729.6 to 2,201.6 MHz, GPU clocks from 306 to 1,300.5 MHz,
and `tj` from 48.875 to 56.437 °C; EMC clock readback was denied. No clock
controls were applied. Raw rail telemetry is retained, not process-attributed
energy. The service exited after the run and port 18883 was closed.

Engine-reported prompt processing took 576.9 seconds at 26.0 tokens/s. The
whole retrieval request took 585.0 seconds, including 8.1 seconds for 41 output
tokens; same-service recovery took 3.9 seconds. These are one-cell observations,
not a performance comparison or a broad 16K support claim. The independently
reviewed result is in `run/independent-review.json`; raw requests, service logs,
clock/memory samples and `tegrastats` are retained beside it.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-prefill128-16k-supervisor --timeout 3600 --interval 1 \
  --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-q2-prefill128/run_recall_case.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/warmup-workload.json \
  --output /tmp/q2-prefill128-16k-run

python3 bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/review_capacity.py \
  --result /tmp/q2-prefill128-16k-run/result.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/workload.json \
  --supervisor /tmp/q2-prefill128-16k-supervisor/result.json \
  --memory /tmp/q2-prefill128-16k-supervisor/memory.jsonl \
  --context 16384 --output /tmp/q2-prefill128-16k-run/independent-review.json
```

The harness and independent reviewer passed `py_compile`; the reviewer also
passed a smoke review against the previously validated 8K selected-profile run.

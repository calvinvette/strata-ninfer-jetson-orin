# Q2_0 selected-profile 64K capacity, retrieval and recovery — Orin — 2026-10-17

The selected Phase 6 Q2_0 MTP-off profile passed one near-limit retrieval and
same-service recovery cell at 64K configured context. The actual uncached prompt
was 60,071 tokens; all three planted codes appeared exactly once and in order,
the model generated 41 tokens, and the same service then returned `RECOVERED`.
The independent review checked the configured context and runtime profile,
exact prompt count, uncached status, marker positions, recovery answer,
supervisor headroom, 28-GiB scope and cgroup memory-event counters.

The configuration matched the selected profile except for the tested context:
Q2_0 GGUF, FP16 KV, MTP off (`--spec 2`, no MTP model), 65,536 context, 3,000
exact expert slots (3,955 MiB), prefill chunk 128, eight workers, prompt cache
disabled, adaptive swaps disabled and a 3,072-MiB workspace reserve. The model
was the `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. Its two shards match the pinned
hashes already recorded in the [32K report](../2026-10-17-phase7-q2-prefill128-32k-selected-profile/artifacts.json).
The pack and profile hashes were rechecked for this run. Model, pack, tokenizer
and profile files stayed under `~/models/strata-orin-validation/`; full
provenance is in [`artifacts.json`](artifacts.json).

The run used a 28-GiB cgroup limit and six-GiB host/admission guard. Minimum
host availability was 16.68 GiB and minimum effective-admission availability
was 11.32 GiB across 2,186 one-second memory samples. The cgroup had zero
`low`, `high`, `max`, `oom` and `oom_kill` events. Engine-reported prompt
processing took 2,251.7 seconds at 26.7 tokens/s; the client request took
2,260.6 seconds, including 8.9 seconds for 41 generated tokens. The same-service
recovery request took 4.0 seconds. The independent review is retained in
`run/independent-review.json`; request output, engine log, supervisor samples
and raw `tegrastats` are retained with this report. These observations describe
one prompt/profile cell, not a comparison or broad 64K support claim.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-prefill128-64k-supervisor --timeout 5400 --interval 1 \
  --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-q2-prefill128/run_recall_case.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128-64k-selected-profile/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-64k-selected-profile/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128-64k-selected-profile/warmup-workload.json \
  --output /tmp/q2-prefill128-64k-run

python3 bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/review_capacity.py \
  --result /tmp/q2-prefill128-64k-run/result.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-64k-selected-profile/workload.json \
  --supervisor /tmp/q2-prefill128-64k-supervisor/result.json \
  --memory /tmp/q2-prefill128-64k-supervisor/memory.jsonl \
  --context 65536 --output /tmp/q2-prefill128-64k-run/independent-review.json
```

The service exited and port 18887 closed after the run. The independent
reviewer passed; this extends the selected profile from 32K to one 64K
capacity point. Broader quality coverage, repetitions, and Phase 7's other exit
gates remain open.

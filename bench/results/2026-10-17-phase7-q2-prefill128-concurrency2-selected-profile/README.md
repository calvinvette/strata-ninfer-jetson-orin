# Q2_0 selected-profile two-slot API concurrency check — Orin — 2026-10-17

The selected Q2_0 MTP-off profile passed one serial-versus-two-slot functional
comparison using distinct 8K and 16K retrieval prompts. The serial control and
two-slot arm each returned 41 tokens for both requests, with exact prompt
counts and all three planted codes exactly once and in order. In the candidate
arm, the runner observed two requests running and two occupied slots at the
same time; one request decoded while the other read its prompt. This qualifies
one overlap sequence only, not general parallel serving.

The tested profile used Q2_0 GGUF, FP16 KV, 16,384 configured context, MTP off,
3,000 exact expert slots (3,955 MiB), prefill chunk 128, eight workers, prompt
cache and adaptive swaps disabled, and a 3,072-MiB workspace reserve. The
candidate arm added two batch slots. The model was the
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. Model, pack, tokenizer and profile
files remained under `~/models/strata-orin-validation/`; hashes and exact input
identity are in [`artifacts.json`](artifacts.json).

The test ran under a 28-GiB cgroup limit and six-GiB host/admission guard.
Minimum host availability was 16.86 GiB and minimum effective-admission
availability was 8.32 GiB across 1,927 samples. Peak cgroup use was 19.68 GiB;
all cgroup pressure and OOM counters stayed zero. Sampled CPU clocks ranged
from 729.6 to 2,201.6 MHz, GPU clocks from 306 to 1,300.5 MHz, and `tj` from
48.812 to 56.750 °C. EMC readback was denied. No clock controls were applied;
raw rail telemetry is retained but is not process-attributed energy.

The serial request elapsed times were 286.9 s at 8K and 525.9 s at 16K. In the
two-slot arm, they were 592.5 s and 1,128.8 s. These are single observations
from a functional comparison, not randomized repetitions or a latency/throughput
claim. They show no serving-latency benefit in this cell. The independent
review, raw requests, engine logs and supervisor telemetry are retained here.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-prefill128-concurrency2-supervisor --timeout 5400 \
  --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/concurrency2/run_api_concurrency.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128-concurrency2-selected-profile/config.json \
  --workload-8k bench/results/2026-10-17-phase7-q2-prefill128-concurrency2-selected-profile/workload-8k.json \
  --workload-16k bench/results/2026-10-17-phase7-q2-prefill128-concurrency2-selected-profile/workload-16k.json \
  --warmup bench/results/2026-10-17-phase7-q2-prefill128-concurrency2-selected-profile/warmup-workload.json \
  --output /tmp/q2-prefill128-concurrency2-run

python3 bench/results/2026-10-14-phase7-q2-recall/concurrency2/review_concurrency.py \
  --result /tmp/q2-prefill128-concurrency2-run/result.json \
  --output /tmp/q2-prefill128-concurrency2-run/independent-review.json
```

The reviewer passed and the service exited cleanly; port 18889 closed. Phase 7
remains open for repeated and broader selected-profile quality/service cells.

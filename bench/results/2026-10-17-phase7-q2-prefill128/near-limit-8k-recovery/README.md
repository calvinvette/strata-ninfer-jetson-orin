# Q2_0 selected-profile 8K near-limit recall and recovery — Orin — 2026-10-17

The selected MTP-off Q2_0 profile passed one supervised near-limit recall
request and a same-service recovery request. The configured context was 8,192
tokens; the measured retrieval prompt contained 7,498 uncached tokens and
completed with 41 generated tokens. Three planted codes placed near 10%, 50%
and 90% of the prompt appeared exactly once and in order. The service then
returned `RECOVERED` to a short request. The independent reviewer verified the
actual prompt count, configured context, marker positions and same-service
recovery; its overall result was pass.

The configuration matched the selected Phase 6 profile: Q2_0 GGUF, FP16 KV,
MTP off (`--spec 2`, no MTP model), 8,192 context, 3,000 exact expert-cache
slots, prefill chunk 128, eight CPU workers, prompt cache disabled, adaptive
swaps disabled and a 3,072-MiB workspace reserve. The model was the
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` Q2_0 snapshot
`5348543e0147355ac9cbcb031184a3546350988e`, with the same shard and pack
hashes recorded in the [sustained-profile artifacts](../sustained-512/artifacts.json).
All model, pack, tokenizer and profile files remained under
`~/models/strata-orin-validation/`.

The run used candidate binary SHA256
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built
from source commit `53d7c7a419f214b4133a2319bdcdf127f23ba1c4`. The checkout was
`e83d2d4352bf39767513bed6e9d5c0eb7135a3fa`; engine/backend/CMake/test sources
are unchanged from the candidate build source. The recall took 287.9 seconds
end to end, including 280.2 seconds of prompt processing and 7.7 seconds of
decoding. Same-service recovery took 3.8 seconds. These are observations from
one prompt and are not a performance comparison.

The test ran under a 28-GiB cgroup limit and the six-GiB host-availability
guard. Host availability stayed above 17.95 GiB and effective admission
availability above 11.75 GiB. The cgroup peaked at 16.25 GiB, with zero
`low`, `high`, `max`, `oom` and `oom_kill` events. Sampled CPU clocks ranged
from 729.6 to 2,201.6 MHz and GPU clocks from 306 to 1,300.5 MHz. The `tj`
sensor ranged from 49.375 to 56.75 °C; EMC readback was denied. No clock
controls were applied. Raw rail telemetry is retained and is not a
process-attributed energy measurement. The service exited and the test port
was no longer listening after the run.

This result establishes one retrieval/recovery point for this profile. It does
not qualify other prompts, contexts, tasks, cancellation, teardown or a product
default. The selected profile remains experimental and Phases 6 and 7 remain
open.

The harness passed `py_compile`, CLI parsing and profile assertions before the
run. Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/strata-q2-prefill128-recall-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-q2-prefill128/run_recall_case.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/warmup-workload.json \
  --output /tmp/strata-q2-prefill128-recall-run

python3 bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/review_recall.py \
  --result /tmp/strata-q2-prefill128-recall-run/result.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/workload.json \
  --output /tmp/strata-q2-prefill128-recall-run/independent-review.json
```

Raw API output, service logs, one-second supervisor memory and clock samples,
`tegrastats`, configs, workloads, runner result and the independent review are
retained here. `SHA256SUMS.txt` covers the report artifacts.

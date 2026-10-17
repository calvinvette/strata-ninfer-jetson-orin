# Q2_0 selected-profile three-cycle teardown — Orin — 2026-10-17

The selected Phase 6 Q2_0 profile passed three sequential fresh-service cycles.
Each cycle completed a distinct 512-token warmup and an uncached 7,498-token
retrieval request with a 41-token answer. All three answers returned the same
three planted codes exactly once and in order. The harness confirmed that each
listener and Strata engine process exited before the next service started. An
independent reviewer checked all three retained responses, token counts,
context setting, and process teardown; it passed.

This used the pinned `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`
Q2_0 two-shard snapshot and the selected experimental profile: FP16 KV, 8,192
context, no MTP model (`--spec 2` verifier setting), 3,000 exact expert slots,
prefill chunk 128, eight workers, prompt cache and adaptive swaps disabled,
and a 3,072-MiB workspace reserve. Model, packs, and tokenizer remained under
`~/models/strata-orin-validation/`.

The supervised run took 996.1 seconds across service startup, warmups, measured
requests, and teardown. Measured request times were 313.3, 276.4, and 276.5
seconds. The first-cycle difference is consistent with file-cache warming; this
three-cycle lifecycle check is not a paired performance comparison. The
supervisor observed a minimum 18.04 GiB host availability and 8.46 GiB
effective admission availability, above the six-GiB physical-host floor. Its
28-GiB cgroup peaked at 19.54 GiB; `low`, `high`, `max`, `oom`, and `oom_kill`
counters remained zero. Sampled CPU clocks ranged from 729.6 to 2,201.6 MHz,
GPU clocks from 306 to 1,300.5 MHz, and `tj` temperature from 48.312 to
56.531 °C. EMC readback was denied; clocks were observed only and not changed.
Raw rail samples are retained, but this run does not measure process-attributed
energy.

The candidate binary SHA256 was
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`; its
source build commit was `53d7c7a419f214b4133a2319bdcdf127f23ba1c4`. The
checkout was `4981af3c1e6d921cf08f53531046831e6629ec24`. The successful run's
full inputs, raw requests, engine logs, supervisor samples, independent review,
and hashes are retained here. Ports 18860–18862 were closed after the run.

This establishes repeated startup, one near-limit retrieval, and teardown for
this profile and workload. It does not establish a general support guarantee,
other contexts or tasks, a performance win, or process-energy efficiency.
Phase 6 and Phase 7 remain open.

The harness and reviewer were checked before/after the run. To repeat the
campaign from the repository root under the same memory guard:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/strata-q2-teardown-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 tools/integration/repeated_service_teardown.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128/teardown-3cycle/config.json \
  --workloads bench/results/2026-10-17-phase7-q2-prefill128/teardown-3cycle/workloads.json \
  --warmup-workloads bench/results/2026-10-17-phase7-q2-prefill128/teardown-3cycle/warmup-workloads.json \
  --output /tmp/strata-q2-teardown-run --cycles 3 --first-port 18860

python3 bench/results/2026-10-17-phase7-q2-prefill128/teardown-3cycle/review_teardown.py \
  --root bench/results/2026-10-17-phase7-q2-prefill128/teardown-3cycle \
  --output /tmp/strata-q2-teardown-review.json
```

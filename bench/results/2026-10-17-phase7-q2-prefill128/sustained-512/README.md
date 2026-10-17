# Q2_0 selected-profile 30-minute streaming soak — Orin — 2026-10-17

The Phase 6 selected Q2_0 test profile completed a supervised 30-minute
uncached retrieval-plus-arithmetic streaming run on Orin1. The runner's
measured interval was 1,802.4 seconds and covered 101 repeated 512-token
requests. Every response returned the exact answer
`EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`.
An independent reviewer checked the exact answer, all three codes, the 512-token
uncached prompt and successful completion for every request. Its overall result
was pass.

The serving profile was Q2_0 GGUF, FP16 KV, 8,192 configured context, MTP off
(`--spec 2`, no MTP model), 3,000 exact expert-cache slots, prefill chunk 128,
eight CPU workers, prompt cache disabled, adaptive swaps disabled and a
3,072-MiB workspace reserve. Every request used 512 prompt and 47 completion
tokens. The model is the two-shard Q2_0 variant from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. The shards have SHA256 values
`69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720` and
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
The model, pack, tokenizer and profile remained under
`~/models/strata-orin-validation/`.

The run used candidate binary SHA256
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built
from source commit `53d7c7a419f214b4133a2319bdcdf127f23ba1c4`. The checkout was
`e83d2d4352bf39767513bed6e9d5c0eb7135a3fa`; engine/backend/CMake/test sources
are unchanged from the candidate build source. The selected run config,
workload and warmup hashes are in `SHA256SUMS.txt`.

Host availability never fell below 17.73 GiB and effective admission
availability never fell below 8.51 GiB during the measured interval. This
cleared the required six-GiB host floor. The 28-GiB cgroup peaked at 19.49 GiB;
`low`, `high`, `max`, `oom` and `oom_kill` event counters remained zero. The
runner shut down the service cleanly, and no service process remained on the
test port afterward.

The first ten request times had a 28.42-second median; the last ten had a
16.32-second median, while the full-run median was 16.36 seconds. The first
requests incurred cold file reads; later requests benefited from warmed OS
file cache. These are observations within this repeated workload, not a
paired performance claim. During the measured interval, sampled CPU clocks
ranged from 729.6 to 2,201.6 MHz and GPU clocks from 408 to 1,300.5 MHz.
Junction temperature ranged from 48.5 to 59.906 °C. Five-minute median
temperature was 55.218 °C for minutes 20–25 and 55.296 °C for minutes 25–30,
consistent with thermal stabilization in the final ten minutes. EMC clock
readback was denied. No clock controls were applied.

Raw `tegrastats` rail readings during the measured interval ranged from 5,763
to 9,606 mW on `VIN_SYS_5V0`, 398 to 11,572 mW on `VDD_CPU_CV`, and 5,191 to
25,149 mW on `VDD_GPU_SOC`. These include board idle and background activity;
they are not process-attributed energy and were not integrated into an energy
claim. The captured telemetry does not independently expose thermal-throttle
state, so this report makes no no-throttling claim.

The test qualifies one 8K-context, short-prompt workload on the selected
profile. It does not establish near-limit recall, long-context quality,
cancellation or teardown behavior for this profile, broad task quality,
process-attributed energy, or a product default. Those gates remain open under
Phases 6 and 7.

The harness passed `py_compile`, CLI parsing, profile/workload assertions and
an independent reviewer check that accepted a correct synthetic response and
rejected an incorrect sum before the run. Reproduce the measured run from the
repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/strata-q2-prefill128-soak-supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/run_sustained.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/warmup-workload.json \
  --output /tmp/strata-q2-prefill128-soak --duration-seconds 1800

python3 bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/review_sustained.py \
  --result /tmp/strata-q2-prefill128-soak/result.json \
  --requests /tmp/strata-q2-prefill128-soak/requests.jsonl \
  --output /tmp/strata-q2-prefill128-soak/independent-review.json
```

Raw one-second memory, clock and `tegrastats` samples, service logs, request
records, runner summaries, the independent review and all input artifacts are
retained here. `SHA256SUMS.txt` covers these report artifacts.

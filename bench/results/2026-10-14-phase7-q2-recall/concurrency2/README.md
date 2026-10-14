# Q2_0 streamed API concurrency-2 check

This Phase 7 screen checks independent retrieval tasks through Strata's
OpenAI-compatible streaming API with two requested batch slots. It is a
functional qualification for this profile, not a throughput win or a general
concurrency support claim.

The Qwen3.8-Flash-Next GSQ RCO Q2_0 cohort used FP16 KV, 16,384 configured
context, 3,000 expert-cache slots, prefill chunk 512, MTP4, prompt cache off,
and the six-GiB host headroom/three-GiB workspace reserve. The serial control
and two-slot service each ran the exact 7,498- and 15,003-token retrieval
prompts. All four responses returned 41 tokens and all three expected markers
exactly once and in order. An independent reviewer verified each retained
response. The two candidate API calls overlapped: `/metrics` observed two
requests running and two active slots; one slot was reading a prompt while the
other decoded. The engine's batch log reported average decode row width 1.00
for both requests, so this run demonstrates overlapping request lifecycle
work, not multi-row decode throughput.

An initial candidate using `--adapt-accepted-only` was rejected by the engine
at startup with `--adapt-accepted-only requires single-request --serve with
blocking, single-GPU adaptive swaps`. That failed cell is retained in
`supervised-run1/`. The successful comparison disabled swaps with
`--adapt-swaps 0` in both arms while keeping MTP4 and the other profile factors
fixed. A first launch was interrupted during model startup before readiness and
before any request; its partial log is retained in `initial-aborted-preflight/`
and is not measurement evidence.

The successful 28-GiB supervisor passed after 1,387.5 seconds. Minimum
physical host availability was 15.66 GiB; minimum effective admission
availability was 7.36 GiB; peak scope use was 20.64 GiB; and peak system swap
use was 3.28 GiB. Sampled cgroup `low`, `high`, `max`, `oom`, and `oom_kill`
counters were zero. Tegrastats `tj` ranged from 51.3 to 58.4 °C. Clocks were
observed dynamically; EMC frequency access was denied, and energy was not
process-attributed.

The serial client latencies were 149.3 seconds for the 8K request and 258.5
seconds for the 16K request. In the two-slot arm they were 881.6 and 728.8
seconds, respectively; TTFT was 871.4 and 336.7 seconds. These are single
serial-versus-batch observations under dynamic clocks, not a paired performance
estimate. They show that admission of two requests did not improve this
workload's latency. Keep parallel serving opt-in and do not qualify
accepted-only adaptive swaps for batch mode from this evidence.

The service binary SHA256 was
`e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`; the
swap-disabled config SHA256 was
`3845b1e4f3d2a29a2e6538f3af6f8bcd7be654287e8f774763e69cf110d92315`. The two
workload SHA256 values are recorded in `supervised-run2/result.json`. Artifact
identity and sizes are in the parent [Q2_0 retrieval report](../README.md).

## Reproduction

From the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/concurrency2/supervisor-run2 \
  --timeout 4800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/concurrency2/run_api_concurrency.py \
  --config bench/results/2026-10-14-phase7-q2-recall/concurrency2/config-swaps-disabled.json \
  --workload-8k bench/results/2026-10-14-phase7-q2-recall/workloads/workload-8192.json \
  --workload-16k bench/results/2026-10-14-phase7-q2-recall/workloads-16384/workload-16384.json \
  --warmup bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output bench/results/2026-10-14-phase7-q2-recall/concurrency2/supervised-run2

python3 bench/results/2026-10-14-phase7-q2-recall/concurrency2/review_concurrency.py \
  --result bench/results/2026-10-14-phase7-q2-recall/concurrency2/supervised-run2/result.json \
  --output bench/results/2026-10-14-phase7-q2-recall/concurrency2/quality-review.json
```

The runner and reviewer are retained here. The reviewer checks exact prompt and
completion counts, uncached prompts, marker count/order, two-slot admission,
and observed two-request/two-slot overlap.

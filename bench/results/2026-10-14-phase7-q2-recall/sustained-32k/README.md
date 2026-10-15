# Q2_0 30-minute sustained retrieval at 32K context

This extends the Q2_0 sustained-service checks to a 32K configured context.
It qualifies one repeated retrieval workload under one opt-in profile, not
broad quality or a general capacity boundary.

The Orin run used the Qwen3.8-Flash-Next GSQ RCO Q2_0 artifacts, accepted-only
MTP4, FP16 KV, 32,768 configured context, 3,000 requested expert-cache slots,
prefill chunk 512, prompt cache disabled, and the existing six-GiB host
headroom/three-GiB workspace reserve. A 512-token warmup and 30,032-token
retrieval precondition passed. The 30-minute serial stream interval measured
2,298.0 seconds (38.3 minutes) and completed four requests; the fourth request
began before the 30-minute deadline and was allowed to finish. Each request
read exactly 30,032 prompt tokens without cache reuse, generated 41 tokens,
and returned all three expected markers exactly once and in order. The
independent reviewer checked each retained response. There were no request
failures.

The 28-GiB supervisor passed after 2,988.2 seconds. Minimum physical host
availability was 16.29 GiB and minimum effective admission availability was
10.27 GiB. Peak sampled scope use was 17.73 GiB and peak system swap use was
3.31 GiB. Sampled cgroup `low`, `high`, `max`, `oom`, and `oom_kill` counters
were zero. Tegrastats `tj` ranged from 49.2 to 57.5 °C; the first and last
five-minute means were 51.6 and 52.7 °C. Clocks were observed dynamically;
EMC frequency access was denied, and energy was not process-attributed.

Median repeated-request latency was 575.1 seconds and median first-visible
token time was 571.0 seconds. These are descriptive single-run measurements,
not a paired performance comparison. Every request reprocessed the full
prompt. The exact model cohort and artifact sizes are recorded in the parent
[Q2_0 retrieval report](../README.md); model artifacts remained under
`~/models`.

The service binary SHA256 was
`e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`, config
SHA256 `18ced34f07c6110c396915e287818419824ff33807e51b3a4906a5d507656ec2`,
and workload SHA256
`c8ce3665d7f6c538c958803c4030f7b290663c2f94b7e6369e87ba2ff5492c8d`.

## Reproduction

From the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-32k/supervisor \
  --timeout 5400 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/sustained-8k/run_sustained.py \
  --config bench/results/2026-10-14-phase7-q2-recall/sustained-32k/config.json \
  --workload bench/results/2026-10-14-phase7-q2-recall/workloads-32768/workload-32768.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-32k/run \
  --duration-seconds 1800

python3 bench/results/2026-10-14-phase7-q2-recall/sustained-32k/review_sustained.py \
  --result bench/results/2026-10-14-phase7-q2-recall/sustained-32k/run/result.json \
  --requests bench/results/2026-10-14-phase7-q2-recall/sustained-32k/run/requests.jsonl \
  --expected-prompt-tokens 30032 \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-32k/quality-review.json
```

Request rows, engine log, config, reviewer output, supervisor samples, clock
observations and tegrastats are retained here and covered by
`SHA256SUMS.txt`.

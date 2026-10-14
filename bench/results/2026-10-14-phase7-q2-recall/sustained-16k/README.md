# Q2_0 30-minute sustained retrieval at 16K context

This extends the Q2_0 sustained-service check from 8K to a 16K configured
context. It qualifies one opt-in profile on one repeated retrieval workload;
it is not a broad quality test or a general capacity claim.

The Orin run used the Qwen3.8-Flash-Next GSQ RCO Q2_0 artifacts, accepted-only
MTP4, FP16 KV, 16,384 configured context, 3,000 requested expert-cache slots,
prefill chunk 512, prompt cache disabled, and the existing six-GiB host
headroom/three-GiB workspace reserve. A 512-token warmup preceded a 15,003-token
retrieval precondition. The serial stream loop then ran for 1,924.2 seconds
(32.1 minutes) and completed eight requests. Each request read exactly 15,003
prompt tokens with no cache reuse, generated 41 tokens, and returned the three
expected markers exactly once and in order. An independent reviewer checked
all eight retained responses; all passed. No request failed.

The 28-GiB supervisor passed after 2,273.7 seconds. Minimum physical host
availability was 16.75 GiB, minimum effective admission availability was
9.77 GiB, peak sampled scope use was 18.23 GiB, and peak system swap use was
3.27 GiB. Sampled cgroup `low`, `high`, `max`, `oom`, and `oom_kill` counters
were zero. Tegrastats `tj` ranged from 49.5 to 58.5 °C; the first and last
five-minute means were 51.7 and 54.6 °C. Clocks were observed dynamically;
EMC frequency access was denied, and energy was not process-attributed.

Median repeated-request latency was 237.87 seconds and median first-visible
token time was 234.12 seconds. These are descriptive single-run measurements,
not a paired comparison. The full prompt was reprocessed on every request.
The configuration's model paths point into `~/models`; model artifacts remain
there. The exact model cohort and artifact sizes are recorded in the parent
[Q2_0 retrieval report](../README.md).

The run used candidate binary SHA256
`e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`, config
SHA256 `bd6e0df5ffc96eb2e762517cadeaf03fa655868bfa04a76bd439588bd52790d5`,
and workload SHA256
`4a09e4c804fcbbaf555f1f69a1c93e50ca7a37a4c0b8a845f9a46c5f71e5dd41`.
`review_sustained.py` adapts the existing 8K independent row reviewer to
assert this workload's 15,003-token prompt length.

## Reproduction

From the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-16k/supervisor \
  --timeout 4800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase7-q2-recall/sustained-8k/run_sustained.py \
  --config bench/results/2026-10-14-phase7-q2-recall/sustained-16k/config.json \
  --workload bench/results/2026-10-14-phase7-q2-recall/workloads-16384/workload-16384.json \
  --warmup-workload bench/results/2026-10-14-phase7-q2-recall/workloads/warmup-512.json \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-16k/run \
  --duration-seconds 1800

python3 bench/results/2026-10-14-phase7-q2-recall/sustained-16k/review_sustained.py \
  --result bench/results/2026-10-14-phase7-q2-recall/sustained-16k/run/result.json \
  --requests bench/results/2026-10-14-phase7-q2-recall/sustained-16k/run/requests.jsonl \
  --output bench/results/2026-10-14-phase7-q2-recall/sustained-16k/quality-review.json
```

Per-request rows, engine log, config, quality review, supervisor memory/clock
samples, and tegrastats are retained here and covered by `SHA256SUMS.txt`.

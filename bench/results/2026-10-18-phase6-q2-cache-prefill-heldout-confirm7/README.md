# Q2_0 held-out cache × prefill confirmation — Orin — 2026-10-18

This seven-block randomized confirmation follows the exploratory cache ×
prefill screen in the sibling `2026-10-18-phase6-q2-cache-prefill-long-screen3`
result. It uses a newly generated near-limit retrieval prompt with distinct
marker values (7,506 formatted prompt tokens) so the confirmation task was not
used in screening. The four cells cross exact expert cache capacities of 3,000
and 3,500 slots with prefill chunks of 32 and 128. Every cell starts a fresh
service, uses a separate 512-token warmup, and makes one measured request under
`MemoryMax=28G` with the six-GiB headroom guard.

The model is Q2_0 with FP16 KV, MTP off, 8,192 context, eight workers, prompt
cache disabled and adaptive swaps disabled. Model files and supporting packs
remain under `~/models/strata-orin-validation`; the pinned model revision,
shard hashes, binary identity and configuration are in `artifacts.json`.

The randomized campaign completed all seven blocks and 28 cells. Every measured
request returned the exact expected 41-token answer from exactly 7,506 prompt
tokens. All fresh services passed supervision, exact cache-slot checks and the
six-GiB host/admission floor. The analyzer found 14,411 memory samples; minimum
host availability was 17.47 GiB and minimum effective admission was 11.45 GiB.
Cgroup low/high/max/OOM/OOM-kill counters were zero. GPU clock observations
ranged from 306 MHz to 1,300.5 MHz and CPU observations from 729.6 MHz to
2,201.6 MHz. `tj` ranged from 48.16 to 56.63 °C; EMC readback was unsupported.
Clocks were dynamic, and energy was not analyzed.

| Exact expert slots | Prefill chunk | Median request time | Median prompt rate | Median decode rate |
| ---: | ---: | ---: | ---: | ---: |
| 3,000 | 32 | 673.1 s | 11.2 tok/s | 7.2 tok/s |
| 3,000 | 128 | 273.2 s | 28.1 tok/s | 7.2 tok/s |
| 3,500 | 32 | 664.8 s | 11.4 tok/s | 7.2 tok/s |
| 3,500 | 128 | 268.1 s | 28.6 tok/s | 7.2 tok/s |

Within paired blocks, chunk 128 reduced median request time 59.54% at 3,000
slots (95% paired bootstrap interval −59.80% to −54.93%) and 59.74% at 3,500
slots (−60.82% to −59.59%); all fourteen block effects favored chunk 128.
Changing the cache from 3,000 to 3,500 slots at chunk 32 had a median effect
of −1.22% (−1.83% to +2.07%). At chunk 128 the median effect was −1.73%
(−11.24% to −0.91%); the bootstrap interval is wide and asymmetric with seven
blocks. The cache-by-prefill interaction estimate was −1.18 percentage points
(−4.70 to +0.04 points), so this confirmation does not establish a cache ×
prefill interaction. Results concern this held-out retrieval prompt and tested
Q2_0 profile. They do not establish broad quality, energy, or a general cache
capacity benefit, and no default or profile changed.

The complete per-request data, paired block effects, validation and bootstrap
intervals are retained in `analysis.json`. Memory and tegrastats telemetry are
losslessly gzip-compressed; the analyzer reads either compressed or plain logs.
All seven campaign manifests, request answers, service logs, supervisor records,
model and binary identities are retained. `SHA256SUMS.txt` pins the report
inputs and results. The report is a held-out confirmation of the exploratory
screen, not a claim that Phase 6 is complete.

Reproduce on the Orin with a fresh output directory:

```sh
out=/tmp/q2-cache-prefill-confirm7
mkdir -p "$out"
cp bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/config.json "$out/"
cp bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/warmup-workload.json "$out/"
python3 bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/prepare_workload.py \
  --output "$out/workload-build" --context 8192
cp "$out/workload-build/workload-8192.json" "$out/workload.json"
bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/run_confirm7.sh "$out"
python3 bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/analyze_confirm7.py --root "$out"
```

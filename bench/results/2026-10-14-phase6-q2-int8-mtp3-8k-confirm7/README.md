# Q2_0 int8-KV MTP3 near-limit held-out confirmation — Orin — 2026-10-14

This seven-block randomized Phase 6 confirmation tested an interaction not
covered by the earlier short-prompt int8-KV MTP3 result: MTP-off versus MTP3
on a distinct near-limit retrieval prompt. Each arm used a fresh service, an
8,192-token configured context, int8 KV, 3,000 requested expert-cache slots,
512-token prefill chunks, eight workers, no prompt-prefix cache, and no trace.
The MTP candidate used window 3; the baseline used MTP off. Adaptive residency
was not enabled. Prompt order within each pair was randomized with seed
`20261016`.

The formatted prompt contained exactly 7,501 tokens and placed three new
retrieval keys near 10%, 50%, and 90% of the input. All 14 requests naturally
stopped at 36 output tokens. Every answer returned
`EARLY=COPPER-FERN-482, MIDDLE=NORTH-EMBER-619, LATE=SILVER-OTTER-357`;
all seven paired response strings were identical. MTP3 offered 28 drafts and
accepted 23 in every candidate request.

| Measure | MTP off median | MTP3 median | MTP3 paired change (95% interval) |
| --- | ---: | ---: | ---: |
| Prompt throughput | 59.75 tok/s | 54.85 tok/s | −9.53% (−12.84%, −6.93%) |
| Decode throughput | 4.979 tok/s | 4.844 tok/s | −4.24% (−8.45%, −0.09%) |
| Client first-visible TTFT | 126.24 s | 137.48 s | +10.51% (+7.44%, +14.71%) |
| Client total request time | 132.71 s | 144.11 s | +10.20% (+7.54%, +13.89%) |

Rates use full-resolution per-request engine counters; client latency uses the
streaming request clock. Intervals bootstrap the seven whole paired ratios
(5,000 resamples). Block 0 is a notable outlier: MTP3 ran first and took
257.22 seconds versus 132.84 seconds for the second, MTP-off arm (+93.64%).
The other six paired total-time changes range from +6.62% to +13.89%. The
outlier is retained in the primary analysis; a cold-start or period effect is
possible but was not isolated. Even so, every paired block was slower with
MTP3, so this workload does not support an int8/MTP3 serving win.

All 14 fresh-service runs passed under separate 28-GiB cgroup scopes and the
six-GiB physical-availability guard. Minimum host/admission availability was
16.90/10.19 GiB, and peak scope use was 17.81 GiB. Sampled cgroup low/high/max,
OOM and OOM-kill counters remained zero. Host-wide observed swap use ranged
from 1.32 to 3.28 GiB and is not attributed to these processes. Tegrastats
`tj` ranged from 49.9 to 57.9 °C; sampled GPU clocks ranged from 306 to
1,300.5 MHz under dynamic policy. EMC access was denied. Post-run integration
of named rail readings over each
request window estimated these median values per output token:

| Named rail | MTP off | MTP3 | Paired change (95% interval) |
| --- | ---: | ---: | ---: |
| `VDD_GPU_SOC` | 32.39 J/token | 33.31 J/token | +2.76% (+1.93%, +3.74%) |
| `VDD_CPU_CV` | 9.54 J/token | 11.06 J/token | +15.50% (+13.99%, +17.16%) |
| `VIN_SYS_5V0` | 24.00 J/token | 25.81 J/token | +7.74% (+6.30%, +10.38%) |

These are separate named board-rail estimates. They include board idle and
background activity, use one-second tegrastats samples, are not process-
attributed, and must not be summed as whole-board energy. Treat them as
diagnostic paired evidence for this run.

The first campaign attempt is retained under `campaign/`. It failed at
preflight because the runner pre-created directories that `run_control.py`
requires to create; no service or model request started. The corrected run is
under `campaign-retry1/`. `analysis.py` verifies the exact configuration,
markers, output equality, per-request counters, resource limits and paired
effects. The Q2_0 shards, MTP pack, PLE pack, tokenizer and expert profile
remained under `~/models/strata-orin-validation/`; their checksums are retained
in `model-checksums.txt`.

Reproduce from the repository root:

```sh
python3 bench/results/2026-10-14-phase6-q2-int8-mtp3-8k-confirm7/prepare_workload.py \
  --output /tmp/q2-int8-mtp3-8k-workload-reproduction
python3 bench/results/2026-10-14-phase6-q2-int8-mtp3-8k-confirm7/run_campaign.py \
  --campaign-name campaign-rerun1
python3 bench/results/2026-10-14-phase6-q2-int8-mtp3-8k-confirm7/analyze.py \
  --campaign-name campaign-rerun1 --output analysis-rerun1.json
```

This confirms correctness and a performance regression for one held-out
7,501-token task with int8 KV and MTP3. It does not generalize to other prompts,
KV formats, MTP windows or cache policies; no profile or default is promoted.

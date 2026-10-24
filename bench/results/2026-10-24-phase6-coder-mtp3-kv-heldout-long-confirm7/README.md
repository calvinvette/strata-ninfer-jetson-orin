# Held-out long-prompt MTP3 × KV confirmation

## Result

A randomized, blocked 2×2 MTP-window × KV-format campaign completed 28/28
requests on Orin on 2026-10-24. The held-out task is a 7,501-token retrieval
and arithmetic prompt with expected result:

`EARLY=EMBER-VAULT-317, MIDDLE=SILVER-MAPLE-846, LATE=TIDAL-COPPER-529, SUM=1692`

Every arm returned that exact result and a 45-token completion. Runtime checks
confirmed requested FP16/INT8 KV, 1,934 expert slots, 3,807 MiB actual expert
cache, and MTP window 0 or 3 as assigned. There were seven randomized blocks,
all comparisons used same-day pairs, and the confirmation task differs from the
previous MTP3 × KV × prompt-length screen. No run failed or was excluded.

MTP3 paired effects versus MTP-off (median paired ratio, 95% paired block
bootstrap interval):

| KV | Prompt throughput | Decode throughput | Client TTFT | Client total |
| --- | ---: | ---: | ---: | ---: |
| FP16 | −0.61% (−0.97, −0.50) | −5.49% (−5.78, −4.59) | +0.62% (+0.51, +0.99) | +0.67% (+0.57, +1.03) |
| INT8 | −0.86% (−1.11, −0.75) | −4.19% (−5.26, −3.37) | +0.87% (+0.77, +1.13) | +0.89% (+0.81, +1.19) |

The MTP × KV decode interaction was +0.69% (95% interval +0.33% to +1.75%).
The total-time interaction was +0.15% (−0.14% to +0.62%), including zero.
Drafting and acceptance were 34/28 in each MTP3 cell. This held-out result
confirms a long-prompt decode slowdown for MTP3 on this model and workload;
it does not support a global MTP recommendation or a default change.

## Physical and energy scope

All runs used a 28 GiB cgroup maximum and preserved the campaign's 6 GiB
physical-memory floor. Minimum observed physical and admission availability
were both 16.925 GiB. GPU clock samples ranged from 306.0 to 1300.5 MHz; the
clock profile was dynamic. EMC clock readback was unavailable. No cgroup memory
pressure events were recorded by the campaign supervisor.

All 28 request windows had estimable tegrastats named-rail energy. Per output
token, MTP3 changed the median rails as follows:

| KV | `VDD_CPU_CV` | `VDD_GPU_SOC` | `VIN_SYS_5V0` |
| --- | ---: | ---: | ---: |
| FP16 | +4.18% (+2.77, +5.27) | −0.42% (−0.46, −0.21) | +0.27% (−0.06, +0.55) |
| INT8 | +5.11% (+3.24, +10.65) | −0.27% (−0.40, −0.00) | +0.58% (−0.01, +0.85) |

Intervals are paired block bootstrap 95% intervals. Rails are integrated
separately using piecewise-linear interpolation of one-second samples. Each
window includes idle/background activity and the full request; readings are not
process-attributed. Rails are not summed and do not represent whole-device
energy. This is a named-rail observation, not a Pareto promotion.

## Response model check

The accompanying exploratory model fits log response against six fixed block
indicators, MTP, KV, and MTP×KV (28 observations, rank 10, residual df 18).
The design is full rank, but residual adequacy is weak: absolute standardized
residuals exceed 3 for multiple outcomes. The largest prompt-throughput and
latency residuals are the block-3 INT8/MTP3 arm; the largest decode residual is
the block-0 FP16/MTP3 arm. Therefore model-based intervals are retained as a
diagnostic only. Paired block bootstrap effects above are the primary result;
the model is not used to establish an interaction or promote a setting.

## Identity and reproduction artifacts

The candidate binary SHA256 is
`1f44e7e3713faf9d1e1fee688a69ce5960e21d40c1d0d6071e9831dea53316d6`.
The campaign recorded source commit
`7e8a7b5acc824ed9a9ce9bd30ead82fe34d5a994`, model/config paths, per-arm
commands, exact answers, runtime settings, memory, clock samples and request
measurements. Model files remain under `/home/calvin/models/` and are not
included here.

- `campaign/campaign.json`: complete factorial and paired audit.
- `campaign/final-audit.json`: same-day and residency-qualified comparisons.
- `campaign/block-*/`: per-arm raw request, supervisor and telemetry records.
- `rail-energy.json`, `rail-energy-pairs.csv`: named-rail integration.
- `analyze_rail_energy.py`: energy integration procedure.
- `response-model.json`, `fit_response_model.py`: exploratory response fit.
- `inputs/`: workload and expected-answer inputs.
- `CHECKPOINT-16.md`: intermediate checkpoint history; the final campaign
  supersedes its 16-arm status.
- `SHA256SUMS.txt`: checksums for the final report tree.

The campaign can be audited with:

```sh
python tools/integration/audit_mtp_kv_screen.py \
  bench/results/2026-10-24-phase6-coder-mtp3-kv-heldout-long-confirm7/campaign/campaign.json \
  --run-root bench/results/2026-10-24-phase6-coder-mtp3-kv-heldout-long-confirm7/campaign \
  --output bench/results/2026-10-24-phase6-coder-mtp3-kv-heldout-long-confirm7/campaign/final-audit.json
```

The response fit and energy integration scripts are retained in this directory.
The result is one held-out workload confirmation, not complete Phase 6
qualification. Worker × transfer, graph × speculation and the broader Pareto
profile remain open, as do Phase 5 state and multi-live gates.

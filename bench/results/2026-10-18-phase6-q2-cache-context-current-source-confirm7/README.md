# Current-source Q2_0 cache × context confirmation

This Orin AGX run repeats the held-out 512-token retrieval-plus-arithmetic cache/context experiment against the current Strata source and checks actual cache admission. It is separate evidence from the inherited 2026-10-14 run, which used a different source binary and must not be treated as a current-source result.

The model was `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision `5348543e0147355ac9cbcb031184a3546350988e`, the two-shard Q2_0 GGUF. Shard SHA-256 values and model paths are recorded in `artifacts.json`; model and auxiliary files stayed under `~/models/strata-orin-validation/`. Candidate source was commit `c1eb609d73f6ef4a1f596a6d7984e8e9522208dd`, service binary SHA-256 `dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`. The run harness/tooling was commit `51007dc0ad4f202df378679fd6948a0bf7ac9006`.

## Design and qualification

Seven randomized blocks crossed requested expert-cache arguments 3,000/5,000 with configured context 8,192/16,384. Each of the 28 cells started a fresh service in its own 28-GiB cgroup scope and ran one warmup plus three measured requests. The profile held FP16 KV, prefill chunk 128, eight pool workers, prompt cache disabled, adaptive swaps disabled, and MTP off (`mtp_max=0`). No clock controls were used.

The held-out prompt was exactly 512 tokens and planted three independently specified markers and a suffix-sum oracle (`593 + 248 + 761 = 1602`). All 84 measured answers matched exactly and reported exactly 512 prompt tokens. All seven blocks admitted the requested actual expert slots in every cell: 3,000 or 5,000, with reported expert-cache allocations of 3,955 or 6,591 MiB. Thus cache allocation did not confound the timing contrasts. All supervisors passed. Minimum physical host availability was 15.33 GiB; minimum effective admission availability was 13.50 GiB, above the preserved six-GiB host floor. The per-cell cgroup `low`, `high`, `max`, `oom`, and `oom_kill` event counters all remained zero.

## Results

The metric is engine-reported `prompt_ms + predicted_ms` per request, summarized by the median of three requests per cell and then compared as paired block effects. A negative contrast means the first-listed setting took less time. Bootstrap intervals resample the seven paired blocks (100,000 resamples); they describe this task and profile only.

| Contrast | Median effect | Paired block bootstrap 95% interval |
|---|---:|---:|
| 5,000 vs 3,000 cache at 8K context | +15.41% | −1.00% to +20.22% |
| 5,000 vs 3,000 cache at 16K context | −2.89% | −4.72% to +0.96% |
| 16K vs 8K context at 3,000 cache | +8.43% | +2.49% to +23.26% |
| 16K vs 8K context at 5,000 cache | −0.43% | −1.17% to +2.52% |
| Cache-by-context interaction (cache effect at 16K minus cache effect at 8K) | −13.67 percentage points | −22.32 to −2.30 points |

The cache-size contrasts each include no change. The 16K context setting was slower at 3,000 slots in this task, while the context effect at 5,000 slots includes no change. The negative interaction indicates that the measured context penalty was smaller at 5,000 slots than at 3,000 slots in this run. This interaction is still limited to this one prompt, model format, and runtime profile. These are engine timings, not end-to-end client latency; no energy result is attributed to requests.

During sampling, observed GPU clocks ranged from 306 MHz to 1,300.5 MHz, CPU clocks from 729.6 MHz to 2,201.6 MHz, and `tj` temperature from 52.1 °C to 58.7 °C. EMC clock readback was denied by the system and is unavailable. Raw per-cell `tegrastats.txt` and `memory.jsonl` logs are retained.

No default or recommended profile changed. This does not establish a general cache or context performance choice. Phase 6 remains open.

## Reproduction and files

`analysis.json` contains each cell's request timings, actual slots, memory minima, validation flags, contrasts, and bootstrap intervals. `workloads.json`, `config.json`, `confirmation-design.json`, source/model identities, and all per-cell logs accompany the report. The initial shared-scope attempt is retained under `retry-lockfix/` as a failed harness attempt and is excluded from the seven-block analysis; the qualified run is under `per-cell-scopes/`.

Re-run qualification and analysis with:

```sh
python3 bench/results/2026-10-18-phase6-q2-cache-context-current-source-confirm7/analyze_confirm7.py
```

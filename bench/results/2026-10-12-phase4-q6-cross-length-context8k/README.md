# Q6_K warp-layout cross-length confirmation at 8K context

Date: 2026-10-12. Device: Orin AGX, ARM64, CUDA 12.6. This is a seven-pair,
same-day confirmation of the existing opt-in `STRATA_Q6K_WARP_DEQUANT=1`
route. It keeps the default route unchanged.

Both arms used the same local IQ1_M Coder model, Q2 MTP artifacts, native GGUF
format, 3,000 requested expert-cache slots, FP16 KV, speculation window 4,
prefill chunk 64, eight workers, mmap experts, and disabled CPU-prefill sharing.
The configured maximum context was 8,192 in both arms. The only configuration
difference was the opt-in environment variable. The executable SHA256 was
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`; actual
cache capacity was 3,903 slots in all 14 measured processes. Both measured
formatted prompts were newly constructed with the checked-in tokenizer
artifacts: 512 prompt/64 generated tokens and 2,048 prompt/128 generated
tokens. Each process first received a distinct exact-length warmup for each
cell. Workload order and arm order were randomized within each pair.

Every measured request passed its exact prompt and completion count, fresh
prefill (`cache_n=0`), and returned identical text between arms in all seven
pairs per cell. The 512-token output digest was stable across pairs. The
2,048-token workload produced two output digests across the seven pairs, but
each baseline/candidate pair matched; the draft and accepted-draft counts also
matched within every pair. This is output parity for these controls, not a
task-quality evaluation.

| Cell | Measure | Baseline median | Candidate median | Paired candidate delta | Paired bootstrap 95% interval |
| --- | --- | ---: | ---: | ---: | ---: |
| 512/64 | Request (`prompt_ms + predicted_ms`) | 21,506.5 ms | 20,016.5 ms | −6.73% | −8.05% to −5.26% |
| 512/64 | Prompt | 17,743.8 ms | 16,216.0 ms | −8.54% | −9.91% to −6.41% |
| 512/64 | Decode | 3,735.1 ms | 3,778.4 ms | +0.22% | +0.07% to +1.19% |
| 2,048/128 | Request (`prompt_ms + predicted_ms`) | 63,699.3 ms | 59,891.5 ms | −5.98% | −7.93% to −5.35% |
| 2,048/128 | Prompt | 56,117.7 ms | 52,345.9 ms | −6.72% | −7.95% to −6.11% |
| 2,048/128 | Decode | 7,597.6 ms | 7,632.9 ms | −0.10% | −0.92% to +0.20% |

Intervals resample seven whole paired deltas (200,000 replicates per metric;
fixed seeds recorded in `analysis.json`). Request-time medians reflect the API
stage timings, not process startup. The independent client wall-time medians
give the same paired deltas to rounding. Minimum host `MemAvailable` was
13.014 GiB, above the six-GiB supervisor floor. Read-only samples observed
CPU frequencies from 729.6 to 2,201.6 MHz, GPU frequencies from 306 to
1,300.5 MHz, and EMC at 3,199 MHz throughout. Clocks were dynamic and energy
was not measured.

The observed request reduction came from prompt processing. Decode was
slightly slower in the 512/64 cell and statistically inconclusive in the
2,048/128 cell. These two workload/context cells are promising timing evidence
for the opt-in route, not a quality result, causal performance model, or
general speedup. The separate [8K accepted-prefix state check](../2026-10-11-phase4-q6-warp-confirmation-8192/README.md#state-and-resource-checks)
matched all four commits and final state for an eight-token request under the
same binary and context; this campaign itself was timing-only and did not
collect accepted-prefix state. The candidate remains opt-in pending task
quality and broader workload/context qualification.

## Reproduction and files

`campaign-retry/` contains all 14 supervisor records, memory/clock samples,
tegrastats, engine logs and API outputs. The initial `campaign/` attempt is
retained: its baseline process loaded the engine, but the harness rejected the
single-cell 2,048-token warmup set before sending any API workload because the
campaign had two measured cells. No measured sample came from that attempt.
`warmup-workloads.json` fixes the cell-count mismatch with distinct 512- and
2,048-token warmups. `analyze.py` rechecks per-request lengths, paired text,
cache capacity and the memory floor before writing `analysis.json`.

```sh
python3 bench/results/2026-10-12-phase4-q6-cross-length-context8k/analyze.py
python3 tools/integration/run_paired_controls.py \
  --baseline-config bench/results/2026-10-12-phase4-q6-cross-length-context8k/baseline-config.json \
  --candidate-config bench/results/2026-10-12-phase4-q6-cross-length-context8k/candidate-config.json \
  --workloads bench/results/2026-10-12-phase4-q6-cross-length-context8k/workloads.json \
  --warmup-workloads bench/results/2026-10-12-phase4-q6-cross-length-context8k/warmup-workloads.json \
  --output bench/results/NEW/campaign --blocks 7 --seed 202610128 \
  --no-trace --privileged-emc
```

The EMC option reads the clock through noninteractive `sudo -n`; it does not
change clocks. Models and MTP artifacts stayed in `~/models/`. Hashes for the
executable, configs, tokenizer, prompts and harness are recorded in
`SHA256SUMS.txt`; no model or build product is tracked.

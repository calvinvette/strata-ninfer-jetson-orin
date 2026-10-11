# Q6_K-to-FP16 warp-layout candidate — Orin — 2026-10-11

The measured dense Q6_K-to-FP16 conversion used 22.4% of summed CUDA kernel
time in the 512/64 request profile. The existing kernel assigns one thread to
each 32-value packed group and writes those values serially. This experiment
adds an opt-in layout where one lane writes one output and each warp owns one
packed group, giving contiguous stores and less serial work per thread. The
Q6_K decode equation and nearest-even FP16 conversion are unchanged. The new
runtime route is selected only by setting `STRATA_Q6K_WARP_DEQUANT=1` before
engine startup; default dispatch and other output types remain unchanged. No
NInfer source was copied.

## Operator screen

The test-only screen compared the production 256-thread kernel, the earlier
group-per-thread 128/256/512 candidates, and the new warp-per-group 128/256/512
candidates on the five real IQ1_M matrices used by the request profile. Each
of three independent processes randomized seven paired shape/schedule blocks
and timed 20 launches per sample after five warmups. Every schedule was
bit-identical to production over all 76,349,440 outputs in each process. The
independent real-artifact CPU/nearest-half oracle also passes 51,200 values
across four rows of each matrix shape in
[`q6-real-payload`](../2026-10-10-phase4-q6-real-payload/README.md).

Warp128 was fastest on all five shapes in all three processes. The paired
medians below are medians of each process's seven block-level measurements;
the ranges show the three process medians, not confidence intervals.

| Rows × columns | Production median (ms) | Warp128 median (ms) | Warp128 delta range across processes |
| ---: | ---: | ---: | ---: |
| 6144 × 2560 | 2.361 | 1.205 | −49.0% to −48.8% |
| 640 × 2560 | 0.251 | 0.123 | −52.7% to −48.2% |
| 10240 × 2560 | 3.941 | 2.004 | −49.3% to −49.0% |
| 512 × 2560 | 0.198 | 0.083 | −58.4% to −56.5% |
| 12288 × 2560 | 4.767 | 2.407 | −49.5% to −49.0% |

Weighting the five matrices by the request profile's measured call counts
(432/208/176/168/40, totaling 1,024 calls) gives seven-block paired reductions
of 49.19%, 49.27% and 49.24% in the three processes. This is an isolated
conversion screen, not a request-time claim. `cuobjdump` reports 20 registers
per thread and zero stack, spills, shared or local memory for Warp128; the
production H16 kernel uses 22 registers with the same zero counts. Occupancy
and hardware bandwidth counters were unavailable. All runs retained at least
27.83 GiB host `MemAvailable`; clocks were dynamic, and no energy result is
claimed. Raw orders, block times, memory and tegrastats are under
`process-reps/`; linked resource counts are in `resource-usage.txt`.

## Held-out request screen

The production route and the opt-in route were compared in three randomized
same-day process pairs on the held-out 2,048-token prompt with 128 generated
tokens. Each process first ran the same distinct 2,048-token warmup. The IQ1_M
model, Q2 MTP, 3,903 actual expert-cache slots, FP16 KV, context 4,096, prefill
chunk 64, eight workers and disabled CPU-prefill sharing were held fixed. Trace
logging was disabled for timing. Each cell passed the six-GiB supervisor; the
lowest host availability was 13.17 GiB. All six requests produced the same
128-token output digest, 180 drafts and 70 accepted drafts, and the engine logs
show 3,903 cache slots in every cell.

| Pair | Baseline request (ms) | Warp request (ms) | Paired request delta | Prompt-time delta | Decode-time delta |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 68,810.9 | 65,970.3 | −4.13% | −4.89% | +1.46% |
| 1 | 69,144.5 | 64,921.8 | −6.11% | −7.14% | +1.54% |
| 2 | 69,764.6 | 65,521.6 | −6.08% | −6.42% | −3.70% |

Request time here is the sum of API `prompt_ms` and `predicted_ms`; it is not
wall time including startup. The median paired request delta is −6.08%. This
three-pair screen is not a seven-pair confirmation and covers one prompt,
context and model policy only. The separate trace-heavy accepted-prefix check
used the same long prompt with eight generated tokens. Baseline and candidate
matched all eight published token IDs, all five accepted-prefix commits, all
eleven full-state fingerprints, final text digest and 3,903 cache slots. That
run is correctness evidence, not timing evidence.

The candidate is promising but remains opt-in. It has not passed held-out
quality tasks or confirmation across additional prompts and contexts, and no
default changed. CUDA and ARM64 execution were tested on Orin. The changed
translation unit compiled in the full HIP build on maestro1; the full SYCL
engine also rebuilt there. Those are compile checks, not backend runtime tests.
Backend logs and pass markers are under `backend-builds/`.

The current Q6_K codec CTest passed 1/1 after the production file change, the
integration Python suite passed 103/103, and the real-payload FP16 oracle passed
both with the environment switch enabled and unset. The unset-environment run
therefore exercises the original default conversion path; its supervised
output is in `real-payload-default/supervisor/`. The enabled run is in
`real-payload-contract/supervisor/`.

## Reproduction

Build the integration harness for CUDA 12.6 / SM87 with the pinned ggml tree,
then run:

```sh
cmake --build build/integration/operator-tests --target q6_k_schedule_sweep --parallel 1
python3 tools/integration/run_control.py \
  --output bench/results/NEW/process-reps/rep1/supervisor --timeout 360 -- \
  build/integration/operator-tests/q6_k_schedule_sweep \
  /home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  20261021
```

For an API comparison, use the paired `baseline-config.json`,
`candidate-config.json`, workload and warmup files in `heldout-screen/` with
`tools/integration/run_paired_controls.py --blocks 3 --no-trace`. The candidate
config differs only by `STRATA_Q6K_WARP_DEQUANT=1`. To check accepted-prefix
state, use the two configs and eight-token workload in `state-check/` without
`--no-trace`.

Source, harness and executable identities are listed in `SHA256SUMS.txt`. All
model files remained under `~/models/`; no build product or model data is
tracked.

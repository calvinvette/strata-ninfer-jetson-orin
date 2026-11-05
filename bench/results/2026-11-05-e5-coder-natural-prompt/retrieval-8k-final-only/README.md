# 8K mixed-codec Coder retrieval state check

Date: 2026-11-05. Jetson Orin AGX, CUDA 12.6. Two fresh-process
Strata/strict-NInfer pairs used an exact 8,192-token prompt under a 16,384-token
context reservation. The task asks for active ticket code `73192` among
repeated closed-ticket distractors. Final-state hashing was enabled;
accepted-prefix tracing was disabled.

## Results

All four requests returned the exact six token IDs
`[22, 18, 16, 24, 17, 248046]`. All 11 final-state fingerprints matched
between backends in each pair and reproduced exactly across both pairs.

| Measure | Pair 1 | Pair 2 |
|---|---:|---:|
| Prompt token count / context | 8,192 / 16,384 | 8,192 / 16,384 |
| Answer and token IDs | `73192`, identical | `73192`, identical |
| All 11 final-state fields | Equal | Equal |
| Supervisor | Pass; min available RAM 20.88 GiB | Pass; min available RAM 20.94 GiB |
| Peak sampled swap / OOM counter | 1.81 GiB / stayed at 1 | 1.71 GiB / stayed at 1 |

These checks cover one retrieval fixture and a static expert profile. They
verify final state, not each intermediate accepted prefix. The arm order was
Strata then NInfer in both pairs, so the prompt/decode timings below are
descriptive only and do not estimate a backend performance effect.

| Pair | Strata prefill | Strict NInfer prefill | Strata decode | Strict NInfer decode |
|---|---:|---:|---:|---:|
| 1 | 373.2 s (22.0 tok/s) | 371.1 s (22.1 tok/s) | 0.97 s (6.2 tok/s) | 0.94 s (6.4 tok/s) |
| 2 | 373.3 s (21.9 tok/s) | 373.9 s (21.9 tok/s) | 0.93 s (6.5 tok/s) | 0.95 s (6.3 tok/s) |

## Identity and limits

Shard names, sizes and SHA-256 values, executable and static profile hashes,
prompt-token hash, state fingerprints and per-arm measurements are in
[`results.json`](results.json). The profile is the existing 391-slot Coder
IQ1_M map. `STRATA_PREFILL_CPU_SHARE=0` was held constant.

Minimum available RAM was 20.88 and 20.94 GiB; sampled swap peaked at 1.81 and
1.71 GiB. The pre-existing cgroup OOM-kill count stayed at one. GPU clocks
were dynamic and uncontrolled; initial GPU readback was 306 MHz, EMC readback
was denied and energy was not computed. Raw process logs and supervisor
telemetry remain local and are not committed.

The configurable harness can reproduce each pair from the integration
worktree:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/retrieval-8k-supervisor \
  --sample-clocks --timeout 3600 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_retrieval_final_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/retrieval-8k-run 8192 16384
```

The run requires the local model shards, tokenizer, qualified executable,
profile and Orin runtime environment. This adds a bounded 8K Coder state and
retrieval point only. It does not qualify all mixed-codec tasks, E6 performance
or E7 release readiness.

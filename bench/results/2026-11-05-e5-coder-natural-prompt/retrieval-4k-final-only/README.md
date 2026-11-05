# 4K mixed-codec Coder retrieval state check

Date: 2026-11-05. Jetson Orin AGX, CUDA 12.6. Two fresh-process
Strata/strict-NInfer pairs used an exact 4,096-token prompt and an 8,192-token
context reservation. The task asks for the active ticket code `73192` among
repeated closed-ticket distractors. Final-state hashing was enabled; accepted-
prefix tracing was disabled.

## Results

All four requests returned `73192` with the same six token IDs
`[22, 18, 16, 24, 17, 248046]`. Across both fresh pairs, all 11 final state
fingerprints matched between Strata and strict NInfer and reproduced exactly:
GDN, PLE, tail, pooled, KV, MTP, stale, dead, pooled-full, previous PLE tokens,
and final length.

| Measure | Pair 1 | Pair 2 |
|---|---:|---:|
| Prompt token count / context | 4,096 / 8,192 | 4,096 / 8,192 |
| Answer and token IDs | `73192`, identical | `73192`, identical |
| All 11 final-state fields | Equal | Equal |
| Supervisor | Pass; min available RAM 20.80 GiB | Pass; min available RAM 21.24 GiB |
| Peak sampled swap / OOM counter | 1.34 GiB / stayed at 1 | 1.86 GiB / stayed at 1 |

These are functional and terminal-state checks for one task and one static
profile. The captured state is final-only; it does not establish every
intermediate accepted prefix. The paired execution order was always Strata
then NInfer, so prompt/decode times below are diagnostic and are not an
order-balanced performance estimate.

## Accepted-prefix trace follow-up

One separately supervised trace-instrumented pair used the exact same prompt
and runtime profile. Both backends again returned the same answer and token
IDs. Persistent-state fingerprints matched at every shared cumulative commit
boundary: 1, 2, 3 and 6 accepted tokens, including all 11 final fields. The
last verifier commit accepted three tokens at once, so this run has no state
snapshot for the two interior token boundaries. This is one trace pair; its
timings are excluded because instrumentation can change scheduling. The
compact per-prefix record is in
[`accepted-prefix.json`](accepted-prefix.json); full trace logs remain local.

| Pair | Strata prefill | Strict NInfer prefill | Strata decode | Strict NInfer decode |
|---|---:|---:|---:|---:|
| 1 | 223.3 s (18.3 tok/s) | 187.9 s (21.8 tok/s) | 0.94 s (6.4 tok/s) | 1.15 s (5.2 tok/s) |
| 2 | 195.8 s (20.9 tok/s) | 197.2 s (20.8 tok/s) | 0.90 s (6.7 tok/s) | 0.93 s (6.4 tok/s) |

## Identity and limits

The exact two model shard names, sizes and SHA-256 values, executable and
profile hashes, prompt-token hash, state fingerprints and per-arm timings are
in [`results.json`](results.json). Both model shards remain in `~/models`.
The profile uses the same 391-slot static Coder IQ1_M profile as the earlier
mixed-codec checks. `STRATA_PREFILL_CPU_SHARE=0` was held constant.

GPU clocks were dynamic and not controlled. The initial GPU readback was
306 MHz; EMC readback was denied. Energy was not computed. Raw per-process
logs and supervisor telemetry remain local and are not committed. The source
runner accepts target prompt and context sizes after its output-directory
argument; omitting them retains the original 2,048/4,096 defaults.

Reproduce one pair from the integration worktree:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/retrieval-4k-supervisor \
  --sample-clocks --timeout 3600 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_retrieval_final_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/retrieval-4k-run 4096 8192
```

The run requires the local model shards, tokenizer, qualified executable,
profile and Orin runtime environment. This adds a bounded 4K Coder correctness
cell and one traced prefix pair; it does not close E5's broader numerical or
quality gates, E6 performance qualification, or E7 release assessment.

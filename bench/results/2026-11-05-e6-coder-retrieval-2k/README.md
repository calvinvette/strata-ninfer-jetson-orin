# Coder IQ1_M 2K retrieval backend screen

Date: 2026-11-05. Jetson AGX Orin, SM87, CUDA 12.6. Four fixed, balanced-order
fresh-process pairs compared Strata and strict NInfer on the same 2,048-token
active-ticket retrieval fixture at a 4,096-token context reservation. The
fixture contains repeated closed-ticket distractors before the active ticket;
it is tokenizer-exact but synthetic. Each arm used one same-prompt eight-token
warmup followed by a measured request. Prefix tracing and state hashing were
disabled.

## Result

All eight measured requests returned `73192`; all four pairs matched the exact
six generated token IDs and passed the answer oracle. Each arm logged 111/2,880
resident expert hits (3.9%). Paired effects are NInfer relative to Strata:

| Pair | Order | Strata decode tok/s | NInfer decode tok/s | Decode change |
| --- | --- | ---: | ---: | ---: |
| 1 | Strata, NInfer | 8.490 | 8.500 | +0.11% |
| 2 | NInfer, Strata | 8.479 | 8.451 | −0.34% |
| 3 | Strata, NInfer | 8.448 | 8.473 | +0.30% |
| 4 | NInfer, Strata | 8.557 | 8.469 | −1.03% |

The paired median decode change was **−0.11%** (four-pair bootstrap screening
interval **−1.03% to +0.30%**). Prompt throughput changed +0.17%
(−1.29% to +0.39%), client TTFT reduction was +0.17% (−1.31% to +0.39%), and
client duration reduction was +0.17% (−1.30% to +0.39%). No metric met the 5%
useful-effect threshold. The small interval is specific to this four-pair,
short-output cell; it does not establish general equivalence. No confirmation
or profile promotion is indicated.

The low resident-hit rate bounds how much work this profile exposes to the GPU
resident expert path. This screen does not isolate performance for all routed
experts or for the staged-miss route. It therefore supplies no evidence of a
useful end-to-end NInfer gain for this 2K retrieval request.

## Resource and capture limits

The supervisor passed the 6 GiB physical-memory floor with 21.25 GiB minimum
available RAM. Sampled swap peaked at 1.82 GiB; the existing cgroup OOM-kill
count remained one. The supervised run took 1,639.4 seconds. Clocks were
sampled read-only and dynamic; EMC readback was denied. Energy was not measured.
`run/results.json` contains per-arm token IDs, timings, pair effects, model and
binary identity, and the runtime options. Raw per-arm logs and supervisor
captures remain in the workspace beside the report.

## Reproduction

From the repository root on Orin:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-retrieval-2k/supervisor \
  --sample-clocks --timeout 1800 -- \
  python3 bench/results/2026-11-05-e6-coder-retrieval-2k/run_retrieval_perf_screen.py \
  bench/results/2026-11-05-e6-coder-retrieval-2k/run
```

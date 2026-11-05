# Coder IQ1_M 512-token prompt repeat

Date: 2026-11-05. Jetson AGX Orin, SM87, CUDA 12.6. This four-pair
order-balanced screen reran the failed Coder `is_prime` screen after extending
the independent arithmetic oracle to accept only `for`, `range`, `int` and
power syntax needed by the generated function. The run used the same exact
512-token prompt, 1,024-token context cap, binary, profile, model shards and
runtime options as the failed cell. Two pairs ran Strata first and two NInfer
first; this sequence was balanced but fixed, not randomized.

## Result

All eight measured requests generated the same 89 token IDs and passed the
11-case executable function oracle. Each pair had the same 1,652/44,640 expert
hits/lookups in both arms. Paired effects are NInfer relative to Strata:

| Pair | Order | Strata decode tok/s | NInfer decode tok/s | Decode change |
| --- | --- | ---: | ---: | ---: |
| 1 | Strata, NInfer | 7.435 | 7.687 | +3.39% |
| 2 | NInfer, Strata | 7.826 | 6.996 | −10.60% |
| 3 | Strata, NInfer | 7.113 | 6.855 | −3.61% |
| 4 | NInfer, Strata | 6.912 | 7.841 | +13.43% |

The paired median decode change was **−0.11%**; the four-pair bootstrap
screening interval was **−10.60% to +13.43%**. Prompt throughput changed
+0.82% (interval −6.53% to +2.97%), client TTFT reduction was +0.80%
(−6.97% to +2.86%), and client duration reduction was +0.92%
(−8.94% to +5.75%). The decode median is below the 5% useful-effect gate and
its interval spans zero. Do not confirm or promote a profile from this screen;
it does not establish equivalence.

The prompt was formed with repeated unrelated filler before the held-out task,
so this is a synthetic prompt-length cell rather than a natural 512-token
quality fixture. One eight-token same-prompt warmup preceded each measurement
in its fresh engine process. Prefix tracing and state hashing were disabled.

## Resource and capture limits

The supervisor passed the 6 GiB physical-memory floor with 21.11 GiB minimum
available RAM. Sampled swap peaked at 1.85 GiB. The existing cgroup OOM-kill
count remained one. Clocks were sampled read-only and dynamic; EMC readback was
denied. Energy was not measured. The supervisor elapsed time was 512.9 s.
Raw per-arm logs, memory samples, clock samples and tegrastats remain alongside
this report. `run/results.json` contains token IDs, arm timings, paired effects,
model hashes and the full runtime identity.

## Reproduction

From the repository root on Orin:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-pp512-tg89-repeat/supervisor \
  --sample-clocks --timeout 1800 -- \
  python3 bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_perf_screen.py \
  bench/results/2026-11-05-e6-coder-pp512-tg89-repeat/run \
  --orders='strata,ninfer;ninfer,strata;strata,ninfer;ninfer,strata' \
  --input-tokens=512 --context-tokens=1024
```

The earlier parser-rejected attempt remains a failed cell with no performance
estimate: [failed-cell report](../2026-11-05-e6-coder-pp512-tg89-screen/README.md).

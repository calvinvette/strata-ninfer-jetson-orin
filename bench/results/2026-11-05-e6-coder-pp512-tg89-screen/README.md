# Coder IQ1_M 512-token prompt performance attempt

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This was intended as a
four-pair, balanced-order Strata versus strict-NInfer screen at a 1,024-token
context cap, using an exact 512-token prompt and the held-out `is_prime`
program task. The prompt reaches 512 tokens by placing repeated unrelated
filler before the task. Each process used an eight-token warmup and then a
natural 89-token answer, with a 128-token output limit.

## Outcome: failed cell, no performance estimate

Three complete pairs ran. Each of the six requests passed the harness's
restricted-AST check, but the runner did not serialize token IDs or aggregate
results until all four pairs finished. In the fourth pair, NInfer generated 91
tokens and the AST checker raised `generated source uses syntax outside the
safe arithmetic subset` before executing the function cases. The runner stopped
before starting the Strata arm, so the final `results.json` was not written.

The logs contain per-arm server timings for the six accepted requests, but not
their generated token IDs, exact pair comparisons, client TTFT/total time, or
an aggregate. Two NInfer requests showed large slowdowns (logged at 1.5 and
6.9 tok/s); the remaining NInfer requests were logged at 6.9–7.8 tok/s and
Strata at 6.9–7.8 tok/s. Because the run is incomplete and the final answer
failed the oracle parser, these partial times are not a backend effect estimate.
The 1.5 tok/s outlier is retained; its cause is unknown. The other two complete NInfer arms were logged at 7.8 and 6.9 tok/s, with Strata at 7.0 and 7.8 tok/s in those blocks. The parser-failed fourth NInfer arm logged 6.9 tok/s, but it has no paired Strata measurement.

The failure is retained explicitly in [`failed-cell.json`](failed-cell.json).
The raw per-process logs and full supervisor captures remain local. The run
passed its resource guard: minimum available RAM was 20.86 GiB against the
6-GiB floor, sampled swap peaked at 1.80 GiB, and the existing cgroup OOM-kill
count remained one. Clocks were dynamic, EMC readback was denied, and energy
was not measured.

The prior 50-token screen remains separate and complete. This prompt-padding
attempt does not establish longer-context quality or performance and does not
warrant a confirmation campaign.

## Reproduction

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-pp512-tg89-screen/supervisor \
  --sample-clocks --timeout 1800 -- \
  python3 bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_perf_screen.py \
  bench/results/2026-11-05-e6-coder-pp512-tg89-screen/run \
  --orders='strata,ninfer;ninfer,strata;strata,ninfer;ninfer,strata' \
  --input-tokens=512 --context-tokens=1024
```

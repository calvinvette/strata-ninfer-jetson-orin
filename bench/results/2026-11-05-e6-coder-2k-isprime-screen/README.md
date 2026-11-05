# Coder IQ1_M 2K function-generation performance screen

Four fixed, order-balanced fresh-process pairs compared Strata with strict
NInfer on a tokenizer-exact 2,048-token prompt and 4,096-token context. The
held-out request asked for `is_prime(n)`; each backend generated the same 91
token IDs and passed the independent 11-case function oracle in every pair.
Each arm first ran an eight-token same-prompt warmup. The static profile used a
6 GiB pinned PCIe complement, `--adapt-every 0`, six GiB RAM headroom and CPU
prefill sharing disabled.

The paired median decode effect was **−1.49% for NInfer**, with the four-pair
bootstrap 95% interval **[−2.40%, −0.42%]**. This is a small measured NInfer
regression on this workload, not a 5% useful gain and not evidence of general
equivalence. Median prompt throughput changed +0.16%; client TTFT reduction
was +0.16%; full client duration reduction was −0.13%, with its interval
spanning zero. Median per-arm decode rates were 8.37 tok/s for Strata and 8.25
tok/s for NInfer. All pairs reported 1,470 resident hits from 33,215 lookups.

The screen used natural generation, fixed synthetic filler and one task. It
does not qualify other contexts, prompts, models or adaptive policies. No
persistent-state capture or independent quality suite beyond the 11 function
cases was run. Minimum sampled host/admission availability was 14.81 GiB,
above the six-GiB floor; the existing OOM-kill count remained one. Clocks were
sampled read-only and dynamic, EMC readback was denied, and energy was not
measured. Raw logs and supervisor samples remain local.

The tracked [`results.json`](results.json) contains paired arms, model/profile
hashes, prompt identity, token checks, quality results, and bootstrap intervals.
Reproduce from the project root on the Orin host:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-11-05-e6-coder-2k-isprime-supervisor-retry \
  --sample-clocks --timeout 10800 -- \
  python3 bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_perf_screen.py \
  bench/results/2026-11-05-e6-coder-2k-isprime-screen \
  '--orders=strata,ninfer;ninfer,strata;strata,ninfer;ninfer,strata' \
  --input-tokens=2048 --context-tokens=4096 \
  --staged-pcie-gib=6 --static-owner
```

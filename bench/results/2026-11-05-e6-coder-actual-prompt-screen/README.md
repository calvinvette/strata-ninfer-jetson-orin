# Coder IQ1_M actual 8K-prompt backend screen

Date: 2026-11-05. Hardware: Jetson Orin AGX (SM87), CUDA 12.6. Four fresh-
process order-balanced pairs compared the same Strata build with its default
expert backend and strict NInfer. The model was Qwen3.8-Flash-Next-GSQ-RCO
Coder IQ1_M, using both GGUF shards, a 256-slot profile, a 16,384-token context,
6 GiB static PCIe complement, `--adapt-every 0`, and CPU prefill sharing off.
The exact 8,192-token prompt was generated from unrelated filler followed by a
held-out `is_prime(n)` function task; this is a synthetic length-controlled
prompt, not natural document or codebase input. Each arm warmed up on the same
prompt before the measured request.

## Results

| Metric | Strata median | Strict NInfer median | Paired NInfer change (median; four-pair screen interval) |
|---|---:|---:|---:|
| Prompt throughput | 53.352 tok/s | 53.344 tok/s | +0.06% (−0.03% to +0.12%) |
| Decode throughput | 8.394 tok/s | 8.356 tok/s | −0.39% (−0.61% to −0.08%) |
| First-token latency | 153.671 s | 153.696 s | 0.06% reduction (−0.03% to +0.12%) |
| Client request duration | 164.425 s | 164.471 s | 0.03% reduction (−0.05% to +0.08%) |

All eight measured responses emitted the same 91 token IDs and passed the
independent 11-case executable oracle. Each pair logged the same 1,470 resident
expert hits from 33,213 lookups for both backends. All four supervised runs
passed the six-GiB available-memory floor; minimum available physical RAM was
14.46 GiB. The supervisor ran for 2,814 seconds. CPU/GPU clocks were observed
but uncontrolled; EMC readback was denied and energy was not measured.

The screen shows a small decode regression for strict NInfer on this workload,
not an end-to-end gain. The four-pair intervals are screening summaries from
this one task/profile, not broad confidence claims. No state capture was used.
The synthetic filler prompt and one code-generation task do not qualify long-
context quality or general backend behavior. E6 and E7 remain open; no profile
is promoted.

## Evidence and reproduction

- [Per-arm measurements and paired summary](input-8192-retry2/results.json)
- [Supervisor result](supervisor-8192-retry2/result.json)
- The raw per-arm logs and telemetry remain local and are intentionally not
  included in Git.

The run used `tools/integration/run_control.py --sample-clocks --timeout
10800` around `bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_perf_screen.py`
with four fixed balanced orders: Strata/NInfer, NInfer/Strata, Strata/NInfer,
NInfer/Strata; `--input-tokens=8192 --context-tokens=16384
--staged-pcie-gib=6 --static-owner`.

Model shard SHA-256 values and the executable/profile hashes are recorded in
the result JSON.

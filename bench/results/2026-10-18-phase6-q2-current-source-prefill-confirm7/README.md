# Current-source Q2_0 prefill chunk confirmation — Orin — 2026-10-18

This seven-block paired confirmation repeated the selected profile's chunk-size
comparison on the current integration candidate. Each randomized block used
fresh services for chunk 32 and chunk 128, exactly 3,000 expert slots, the same
previously qualified 512-token retrieval-plus-arithmetic task, a separate
512-token warmup, and one measured request per cell. The model was the Q2_0
two-shard artifact from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned at revision
`5348543e0147355ac9cbcb031184a3546350988e`. Model files remained under
`~/models/strata-orin-validation/`.

All 14 measured responses exactly matched the independent 47-token answer and
all supervisors passed. The candidate binary was SHA256
`320963c6572a13065e7704b3f98d477c8e29119ea45a96114f532008134e9932`, built
from engine source commit `0b28cd634fa3a7ba9da514df0200d96baea330e4`.
The same 3,000-slot cache, 8K context, FP16 KV, MTP-off setting, eight workers,
3,072-MiB workspace reserve, no prompt cache and no adaptive swaps were used in
every cell.

| Metric | Chunk 32 median | Chunk 128 median | Paired chunk-128 change (95% interval) |
| --- | ---: | ---: | ---: |
| Request time | 47.87 s | 29.09 s | −40.75% (−40.86%, −37.56%) |
| Prompt time | 40.00 s | 20.76 s | −48.21% (−48.50%, −46.49%) |
| Decode time | 7.79 s | 7.87 s | +1.38% (−4.62%, +5.40%) |
| `VIN_SYS_5V0` joules/output token | 6.77 J | 4.14 J | −40.04% (−40.53%, −37.74%) |
| `VDD_GPU_SOC` joules/output token | 8.98 J | 5.53 J | −38.24% (−39.14%, −37.42%) |

Intervals use 100,000 bootstrap resamples of seven paired block effects. Every
request-window energy estimate was supported by bracketing tegrastats samples
with no sampling gap over 2.5 seconds. Named rails are integrated separately;
the estimates include board idle and background activity and are not process
energy. The rails must not be summed. The result supports the chunk-128 choice
for this exact workload and profile on the current binary; it does not establish
a general workload effect or justify a default change. Decode time was
inconclusive. The same 512-token task was used in earlier Q2_0 profile
qualification, so this is a current-source repeat rather than a new held-out
prompt.

Across 1,209 one-second memory samples, minimum host availability was 18.06
GiB and minimum effective admission availability was 14.70 GiB. All sampled
cgroup low/high/max/OOM/OOM-kill counters were zero. GPU clocks ranged from
306 MHz to 1,300.5 MHz and CPU clocks from 729.6 MHz to 2,201.6 MHz; EMC
readback was denied. Clocks remained dynamic and uncontrolled.

The raw per-cell requests, configurations, service logs, supervisor results,
memory samples and tegrastats readings are retained by block. Reproduce on
Orin with a fresh output directory:

```sh
bench/results/2026-10-18-phase6-q2-current-source-prefill-confirm7/run_confirm7.sh \
  /tmp/q2-current-source-prefill-confirm7
```

The script copies the pinned configuration and workload into that directory,
runs all randomized pairs with isolated 28-GiB scopes, then regenerates the
analysis, CSV summaries and SVG figure. `SHA256SUMS.txt` covers the committed
evidence. This current-source repeat does not close Phase 6's other interactions
or process-attributed energy work.

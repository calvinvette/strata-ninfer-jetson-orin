# Q2_0 128-token request cache-policy confirmation

Date: 2026-10-31. Device, binary, model artifacts and runtime profile match the
[8K cache-policy screen](../2026-10-31-e6-q2-cache-size-screen/README.md).
Seven randomized independent-process pairs compared strict NInfer at configured
3,000- and 4,000-slot cache capacities. Both arms used the default adaptive
swap policy. Context reservation was 8,192 tokens. Each process warmed and
measured two heldout 512-token retrieval prompts with a 128-token generation
limit. Temperature was zero, prompt cache and tracing were off, and the only
runtime argument changed between arms was `--expert-cache`.

The preliminary fixed-length pilot had marked the ORBIT task incomplete when
3K naturally stopped at 117 tokens. This confirmation enables the harness's
natural-stop qualification and records actual output counts. That keeps real
serving behavior in scope and avoids treating early EOS as an execution error.

## Paired results

Positive advantage means 4K is faster. Intervals use 100,000 paired bootstrap
resamples over seven independent process pairs.

| Heldout task | Metric | 3K median | 4K median | 4K advantage (95% interval) |
| --- | --- | ---: | ---: | ---: |
| `NIMBUS-7319` | Prompt TPS | 24.82 tok/s | 23.89 tok/s | −3.63% (−6.98%, −3.39%) |
| | Decode TPS | 7.99 tok/s | 8.80 tok/s | **+10.10% (+9.91%, +10.53%)** |
| | First-visible TTFT | 20.92 s | 21.73 s | −3.85% (−7.81%, −3.23%) |
| | Client total | 36.72 s | 35.94 s | +1.11% (−0.22%, +2.13%) |
| `ORBIT-4826` | Prompt TPS | 25.70 tok/s | 25.91 tok/s | +0.39% (−3.65%, +2.62%) |
| | Decode TPS | 7.68 tok/s | 8.73 tok/s | **+12.45% (+4.83%, +15.97%)** |
| | First-visible TTFT | 20.21 s | 20.03 s | +0.44% (−4.23%, +2.54%) |
| | Client total | 35.20 s | 34.58 s | +1.34% (−1.39%, +3.13%) |

Decode TPS exceeded the 5% median threshold on both prompts, and both paired
intervals excluded zero. The NIMBUS interval is entirely above 5%; the ORBIT
interval is positive but its lower bound is 4.83%. NIMBUS prompt TPS and TTFT
regressed by under 5% on median; ORBIT prompt TPS and TTFT were effectively
unchanged. NIMBUS client time had equal output lengths. ORBIT client-total time
is not a clean equal-work comparison because output lengths differ.

All 28 measured responses started with the exact requested retrieval value.
NIMBUS generated 128 tokens on both arms in every pair. ORBIT generated 117
naturally stopped tokens on 3K and 128 tokens on 4K in every pair. The ORBIT
3K answer completed its explanation; 4K reached the generation cap during its
explanation. This is an output-length/termination difference and prevents a
claim of full-text quality equivalence. It does not invalidate per-token TPS,
which uses each response's actual generated-token count and decode duration.

## Resources and interpretation

All 14 processes and 56 warmup/measured task requests passed natural-stop
qualification. Minimum sampled available RAM was 10.23 GiB; maximum sampled
swap was 2.68 GiB; sampled OOM counters were zero. CPU frequency observations
ranged 729.6–2,201.6 MHz and GPU 306–1,300.5 MHz; EMC readback was denied.
Clocks remained dynamic. No request-attributed energy was measured. The 6 GiB
host floor and 3 GiB workspace reserve remained in force.

This confirms a decode-rate gain for the tested 8K-context, pp512+tg128 Q2_0
retrieval workload with 4K configured capacity and adaptive swaps. It does not
isolate capacity from adaptive ownership, establish a fixed runtime map, or
qualify a general/release profile. NInfer-versus-Strata remains a separate
comparison and did not meet the 5% threshold at the 4K screen. Keep the path
opt-in; E6/E7 remain open. Per-pair observations, output hashes, exact token
counts and derived statistics are in [`paired-summary.json`](paired-summary.json).

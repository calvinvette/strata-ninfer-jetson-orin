# Q2_0 cache-policy held-out confirmation

Date: 2026-10-31. Device, binary, model, compiler, reservation and telemetry
are the same as the [three-pair cache screen](../2026-10-31-e6-q2-cache-size-screen/README.md).
This campaign used seven randomized independent-process pairs at 8,192-token
context reservation. Both arms used strict NInfer, one live request, 512 prompt
tokens and 64 generated tokens. The only configured difference was the startup
expert-cache capacity: 3,000 versus 4,000 slots. Each process warmed both tasks
once and measured each once; task order was paired within block. MTP drafted and
accepted zero tokens.

## Cache behavior and correctness

All 14 processes passed. Across 28 measured requests, both held-out retrieval
answers (`NIMBUS-7319` and `ORBIT-4826`) appeared at the beginning of every
response, and every response contained exactly 64 generated tokens. The
published [paired summary](paired-summary.json) contains per-request metrics,
answer checks and response hashes, but no prompt or response text. The two
answer checks are functional task checks, not broad model-quality equivalence.

The cache profiles have adaptive swaps enabled by default. Logs say the startup
profile has “no eviction” while also stating adaptive swaps exchange profile
experts with the GPU cache. Therefore this comparison evaluates configured
cache capacity **with the default adaptive-swap policy active**. Profile-prefix
hashes identify the startup ranked recipe; they do not identify the runtime
resident map during each request. Variable swap counters were observed. The
experiment cannot isolate slot count from runtime owner changes or establish a
fixed-residency cache-size effect.

## Paired results

Advantage is positive when the candidate is faster. Pair-level bootstrap
intervals use the seven independent process pairs (100,000 resamples).

| Held-out task | Metric | 3K median | 4K median | 4K advantage (95% interval) |
| --- | --- | ---: | ---: | ---: |
| `NIMBUS-7319` | Prompt TPS | 25.61 tok/s | 25.36 tok/s | −2.16% (−7.27%, +0.94%) |
| | Decode TPS | 7.30 tok/s | 8.69 tok/s | **+17.97% (+11.01%, +22.88%)** |
| | First-visible TTFT | 20.21 s | 20.40 s | −2.47% (−7.78%, +1.02%) |
| | Client total | 28.95 s | 27.53 s | +2.40% (−0.46%, +6.11%) |
| `ORBIT-4826` | Prompt TPS | 25.95 tok/s | 25.91 tok/s | −2.28% (−7.37%, +2.96%) |
| | Decode TPS | 7.23 tok/s | 9.22 tok/s | **+25.20% (+23.13%, +28.28%)** |
| | First-visible TTFT | 19.90 s | 19.94 s | −2.20% (−7.78%, +2.58%) |
| | Client total | 28.64 s | 26.71 s | +4.05% (+1.28%, +7.57%) |

Decode TPS clears the preregistered 5% median-and-interval screen on both
tasks. Prompt TPS and first-visible TTFT are slightly slower by less than 5%
on median; client total improves. Descriptive client-total p95 (seven
observations per arm) was 29.81 s vs 30.00 s for task 1 and 29.44 s vs 29.30 s
for task 2. These are task-specific numbers at pp512+tg64, not general service
performance.

## Resources and decision

Minimum process-sampled available physical RAM was 10.25 GiB; maximum sampled
swap use was 2.66 GiB; sampled cgroup OOM-kill counts were zero. CPU clocks
ranged 729.6–2,201.6 MHz and GPU clocks 306–1,300.5 MHz; EMC readback was
denied. Clocks remained dynamic. No request-attributed energy was measured.
The 6 GiB host floor and 3 GiB workspace reserve remained in force.

This confirms 4K plus the default adaptive swaps as a **candidate cache policy
for Q2_0, 8K context, pp512+tg64 retrieval on this device**. It does not
qualify a fixed map, broader workloads, other contexts, or a release profile.
The separate 4K NInfer-versus-Strata screen remains below the 5% end-to-end
threshold; these results are not evidence of a general NInfer backend speedup.
E6/E7 remain open.

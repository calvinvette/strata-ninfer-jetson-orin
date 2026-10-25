# E0 expert runtime audit — Orin — 2026-10-25

This is the first E0 baseline capture for the NInfer expert execution plan. It
freezes the current Strata route and measures its decode path before any NInfer
kernel has been promoted. The NInfer backend is not yet implemented, so there is
no NInfer A/B result here.

## Frozen profile and identity

The run used the Coder IQ1_M model pair at 8K maximum context, one live request,
FP16 KV, a fixed 128-token prefill chunk, eight CPU pool workers and static
expert residency (`--adapt-swaps 0`). Prompt cache was disabled. The existing
Q6_K warp dequantization setting was retained. The native verifier geometry
was enabled with `--spec 2`, but the engine and API counters both reported zero
drafts and zero accepted drafts; MTP was therefore inactive in the measured
requests.

The configured cache request of 3,000 produced 3,903 GPU-resident slots and
7.44 GiB of the Orin's shared physical memory. The profile JSON includes the
exact startup configuration and cache size. The new opt-in dump records the
actual sorted `(layer, expert, slot)` map. Its SHA256 is
`d391d3b8fe1aa0361b6441aecff74279d0946fcb3529099af2eb4d69a4ca2859` for this
profile.

The profiler and initial timing runs used the qualified current candidate built
from source `348e6261ab3fa5f119ec3050637c01477fddaa78`, SHA256
`ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`. The
paired screen and map-dump smoke used a fresh SM87 build from the isolated
`feat/ninfer-expert-e0` worktree, SHA256
`48995208032baeb92877afa953b74f80d288905a1744f32b8dcbb355da3dbd19`. Model
shard, deployment pack, tokenizer and expert profile identities are in
[identities.json](identities.json). Models remain under `~/models/`.

## Decode breakdown

An unprofiled request with the existing opt-in `STRATA_DECODE_TIMING=1`
instrumentation warmed once and then measured 512 prompt tokens plus 64 output
tokens. The measured request produced 64 tokens at 16.1 tok/s; the draft counters
were 0/0. The engine reported:

| Decode component | Per token/window | Across 64 output tokens |
| --- | ---: | ---: |
| Total decode window | 62.10 ms | 3.98 s |
| Verifier wait for GPU reach | 35.07 ms | 2.24 s |
| Per-layer host work | 22.12 ms | 1.42 s |
| └ CPU expert computation within host work | 21.73 ms | 1.39 s |
| └ Plan, activation quantization and job setup | 0.34 ms | 0.02 s |
| Host staging | 0.02 ms | 0.001 s |
| Commit and emit | 0.13 ms | 0.008 s |

Each token averaged 4.44 CPU expert entries and 5.56 GPU-resident hits per
layer-window. The same request reported 17,090 GPU hits among 30,720 lookups
(55.6%). This hit percentage is a routing count, not a time fraction. The CPU
expert measurement is the existing host pool timing; it includes the observed
CPU path and is not an operator-only microbenchmark.

## Nsight diagnostic

Nsight Systems 2024.5.4 profiled one warmup and one measured request each at
512+64 and 2,048+128, under the same 8K profile. The measured 512+64 request
reported 48.1 prompt tokens/s, 14.6 generated tokens/s and 15.02 seconds client
time; the profiler run is diagnostic and is not compared with unprofiled TPS.
The decode kernel window from the first visible token to completion was 4.292
seconds. Within that window, summed GPU kernel durations included:

| Kernel family | Events | Summed duration |
| --- | ---: | ---: |
| NInfer-relevant resident Strata expert gate/up kernels (`native_gu_multi_kernel`) | 6,048 | 255.8 ms |
| Resident Strata expert down kernels (`native_down_multi_kernel`) | 6,048 | 174.5 ms |
| Q6_K dense matrix-vector kernels (`native_q6_k_mmvq_kernel`) | 8,126 | 1,038.2 ms |
| GPU synchronization spin waits (`wait_flag_ge_kernel`) | 9,072 | 883.7 ms |

These are sums across GPU kernel events, not request critical-path time; concurrent
streams and waits make direct division by request duration misleading. The
resident expert kernel families are substantially smaller in summed duration
than dense Q6_K work and synchronization. The host decode timer independently
shows about 1.39 seconds of CPU expert-pool time across this request. These
measurements make a resident-only kernel substitution an incomplete performance
strategy: it cannot improve CPU-served misses, and its GPU gains are bounded by
work outside the resident expert kernels. A bounded staged-GPU route for misses
remains necessary to test the larger expected benefit, with full fetch/copy cost
included as E3 requires.

The current capture has no exact CPU stack attribution. Do not treat these
results as an NInfer performance comparison or as the speedup ceiling: GPU wait
and kernel sums overlap, and the timing run is one block. The raw Nsight report,
SQLite export, CSV summaries, request records, engine logs and physical-memory
telemetry are retained locally under `build/integration/e0-profile/`; they are
intentionally not committed.

## Same-day pinned Strata screen

Three randomized paired processes compared the pinned Strata executable from
commit `0be090c` (SHA256
`edbc0a85fc706fd929f9ea5ad1041c3fed25a0cc107356bcc82e59c2431a5249`) with the
fresh E0 current-Strata build. Each process used one warmup and one measured
512+64 request. The 33 engine arguments and runtime environment were identical;
Q6_K warp dequantization was disabled in both arms. Both arms reported 3,903
slots / 7.44 GiB, zero drafts offered or accepted, 30,720 routed lookups, and
the same response text in every pair.

| Metric | Pinned median | Current median | Paired current/pinned median ratio (95% bootstrap interval) |
| --- | ---: | ---: | ---: |
| Prompt rate | 58.9 tok/s | 58.9 tok/s | 1.000 [0.978, 1.008] |
| Decode rate | 16.1 tok/s | 16.1 tok/s | 1.000 [0.988, 1.000] |
| Client TTFT | 8.765 s | 8.775 s | 1.001 [0.993, 1.023] |
| Client request | 12.667 s | 12.717 s | 1.004 [0.996, 1.016] |

Three pairs are screening evidence, not a performance confirmation. This is a
product-control check across accumulated Strata-fork changes; it does not
estimate an NInfer effect. The pinned binary does not emit its resident ID map,
so its cache is matched by model, profile, options, shared-memory allocation and
slot count, not by a directly measured ID-map hash. The fresh current-source
map hash and full map are recorded above and locally under
`build/integration/e0-profile/`.

Two earlier attempts were excluded: one malformed `--prompt-cache` config was
rejected before model startup; another omitted the frozen zero-suffix-draft
settings and reported three offered drafts. Their raw records remain in the
screen directories and are not included in the table. The corrected campaign,
summary and summarizer are in
[`pinned-vs-current-corrected-screen3/`](pinned-vs-current-corrected-screen3/)
and [summarize_pinned_screen.py](summarize_pinned_screen.py).

## Memory, clocks and next decision

The supervised Nsight capture kept a minimum sampled `MemAvailable` of 13.47
GiB, above the required 6 GiB headroom. Its admission floor was 6 GiB and no
cgroup memory events occurred. CPU clocks ranged from 0.730 to 2.202 GHz; GPU
clocks ranged from 306 to 1,301 MHz. EMC clock readback was unavailable. Energy
was not measured; the supervisor did not alter clocks or stop services.

The opt-in residency dump is off by default. Enabled and disabled smoke
requests produced identical text and decode rates of 16.1 and 16.0 tok/s in
one pair; the disabled run created no map file. This is a functional smoke,
not a powered instrumentation-neutrality test. E0 remains open for a
repeatability confirmation, the pinned binary's resident-ID map, and a matched
same-source backend-off/backend-on pair after E2 adds the selector. The current
finding selects the Q2_0 expert codec pair for E1 contract proof as planned,
while Coder IQ1_M provides the measured mixed-codec prioritization data. The
paired screen's minimum physical/admission availability was 14.15 GiB, with no
cgroup memory events; clocks remained dynamic and EMC readback was unavailable.

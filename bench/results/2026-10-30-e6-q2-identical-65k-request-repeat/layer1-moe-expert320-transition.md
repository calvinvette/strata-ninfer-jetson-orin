# Layer-1 MoE expert-part transition at the final prompt token

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is an instrumented,
same-process request-repeat diagnostic, not a speed result.

## Setup

One strict-NInfer process handled the same 65,536-token prompt twice, with
temperature 0, 32 generated tokens, 131,072 context, prompt cache disabled,
and PCIe staging disabled. An opt-in model-layer-1 MoE bundle captured route
IDs, route weights, the MoE input, ten expert output rows, shared output, and
combined output at prompt position 65,535. Both records have token 271. The
bundle is 266,496 bytes for the two records.

## Findings

Routes, weights, MoE input, and shared-expert output matched exactly. The same
ten experts were selected in the same order:
`383, 32, 97, 235, 400, 320, 193, 206, 70, 74`. Only the output row for expert
320 differed:

| Field | Different values | Maximum absolute difference | Relative L2 |
| --- | ---: | ---: | ---: |
| Route weights | 0 / 10 | 0 | 0 |
| MoE input | 0 / 2,560 | 0 | 0 |
| All expert output rows | 2,220 / 25,600 | 3.18438e-05 | 1.69993e-04 |
| Expert 320 output row | 2,220 / 2,560 | 3.18438e-05 | 5.24514e-04 |
| Each of the other nine expert rows | 0 / 2,560 | 0 | 0 |
| Shared-expert output | 0 / 2,560 | 0 | 0 |
| Combined output | 1,658 / 2,560 | 1.72993e-06 | 5.56115e-05 |

Expert 320 is route index 5 with weight `0.0543313771`. Multiplying its
per-expert output delta by that unchanged route weight predicts the combined
output delta with cosine similarity `0.99999980`; the relative L2 residual
between predicted and observed combined deltas is `6.30e-04`. This ties the
combined difference to this one expert row, subject to normal float summation
order.

An independent scalar Q2_0 × Q8_1 oracle used the captured common F32 input and
the GGUF weights for model layer 1, expert 320. The second request's expert
row matched the oracle to relative L2 `5.79e-08`; the first request's row
differed by relative L2 `5.24529e-04`, with a maximum absolute difference of
`3.18416e-05`. The change between requests is therefore localized to the
expert-320 computation/output row for this pair. The result alone does not
identify whether the changing factor is a weight view, scratch lifetime,
kernel race, or another runtime detail.

## Backend control and focused replay

A second same-process 65K pair used the Strata expert backend with the same
MoE bundle capture. Its repeated request showed the same expert-320 change:
routes, weights, input and shared output were exact; the expert-320 part and
combined output had the same changed-value counts and deltas as the NInfer
pair. More strongly, the per-request route, weight, input, all expert parts,
shared output and combined output were byte-identical between NInfer and
Strata. This run does not show a difference unique to the NInfer backend.

The focused `ninfer_q2_expert_parity` check was extended to replay the exact
one-entry grouped NInfer and Strata dispatch 32 times at fixed input and
weights. Both outputs remained bit-identical across all 32 calls. The direct
NInfer D3/D4 row matched an independent FP64 Q2_0/F32 oracle (relative L2
`1.57e-07`, maximum absolute error `1.34e-08`); grouped NInfer and Strata
outputs matched exactly for the one-entry case. The process passed. Its
interleaved operator timings were 24.510 vs 24.673 microseconds (NInfer /
Strata) for one token, 4,387.924 vs 3,949.398 microseconds for 64 tokens,
and 8,938.040 vs 7,958.909 microseconds for 128 tokens. Those isolated
operator timings do not represent end-to-end serving; the larger grouped
shapes were slower with NInfer in this run.

The service's repeated multi-expert request history is not reproduced by the
fixed-input one-entry replay. The unchanged backend output therefore narrows
the cause to shared service/runtime context (for example, the live expert
weight view or cache-slot ownership) but does not establish which one.

## Service execution ownership capture

A follow-up current-source strict-NInfer run captured the grouped Q8_1 row and
expert-320 resident-cache entry at model layer 1, position 65,535, for the same
65K/32 repeated-request workload. Both capture records used token 271. The
supervised run passed with 8.54 GiB minimum available RAM, 4.52 GiB peak swap,
and zero cgroup OOM kills; instrumentation makes its timing unsuitable as
performance evidence.

| Request | Expert-320 owner evidence | Captured expert weights | Grouped Q8_1 row |
| --- | --- | --- | --- |
| 1 | No GPU resident slot (`slot = -1`) | Not present in the device cache | SHA-256 `61ad484b…fed17599` |
| 2 | GPU resident slot 145 | 1,382,400 bytes; SHA-256 `932d559a…5e42781` | SHA-256 `61ad484b…fed17599` |

The Q8_1 rows were byte-identical (0 of 2,880 bytes changed). The earlier MoE
bundle shows the F32 MoE input was also byte-identical, while the expert-320
output changed. At request 1 expert 320 was not in the GPU grouped dispatch and
was served by the CPU miss path; by request 2 it occupied a GPU cache slot and
went through the resident grouped path. This owner change explains the two
per-expert results: the first differs from the independent GPU Q2_0 × Q8_1
oracle, while the second matches it at relative L2 `5.79e-08`. The changing
row is consistent with a CPU-to-GPU owner transition, rather than a changing
NInfer kernel for fixed GPU inputs.

To check that attribution directly, `native_expert_parity` replayed the
captured F32 MoE input and model-layer-1/expert-320 GGUF weights through
Strata's native CPU path and grouped GPU path. The CPU replay matched request
1's captured service row bit-for-bit; the GPU replay matched request 2's row
bit-for-bit. Comparing the two owners changed 2,220/2,560 output values, with
maximum absolute difference `3.18438e-05` and relative L2 `5.24527e-04`.
The test passed. Together with the prior fixed-input NInfer/Strata grouped
replay, this attributes the captured row change to the cache-driven CPU/GPU
owner transition, not nondeterminism within either tested kernel path.

This also bounds what the integration accelerates. NInfer handles supported
experts only while they are GPU-resident; active routed experts can still be
computed by Strata's CPU pool. The two requests' decode GPU-cache hit rates
were 32.9% and 62.5%, respectively. Future performance comparisons must record
actual expert ownership and hit rates, and distinguish backend arithmetic at
fixed residency from end-to-end cache-policy results. Raw `STMOEX01` records
and supervisor telemetry remain under
`/tmp/e6-65k-moe-exec-service-repeated-3.moe-exec` and
`/tmp/e6-65k-moe-exec-supervisor-4/`.

## Fixed-CPU-owner repeat control

A second same-process 65K/32 strict-NInfer pair disabled cache adaptation
(`--adapt-every 0 --adapt-swaps 0`) to keep the profile-ranked GPU cache fixed.
Expert 320 was CPU-owned at the target layer/position for both requests
(`route_kind = -1`). Both requests had the same prompt-boundary fingerprints
and the same final fingerprints in every recorded persistent-state field.
The complete 133,248-byte layer-1 MoE bundle records were byte-identical
(SHA-256 `a8b809a2…22bc059e`); this includes route IDs/weights, MoE input,
expert rows, shared output and combined output. The decode GPU-cache hit rate
was 12.0% in each request, consistent with the intentionally static cache
policy. The supervised run passed with 8.74 GiB minimum available RAM, 1.64
GiB peak swap and no cgroup OOM kills. This instrumented low-residency control
is correctness evidence, not a performance result. Raw captures and telemetry
remain under `/tmp/e6-65k-moe-fixed-cpu-repeat-2.*` and
`/tmp/e6-65k-moe-fixed-cpu-supervisor-2/`.

## Fixed-GPU-owner repeat control

A second static-cache 65K/32 same-process repeat moved expert 320 to GPU
profile rank 0, disabled adaptation, and confirmed it remained GPU-owned at
layer 1 / position 65,535 in both requests (slot 0, `route_kind = 0`). The
supervised pair passed. Both prompt-boundary fingerprints and all recorded
final-state fingerprints matched exactly. Its two 133,248-byte layer-1 MoE
bundle records were byte-identical (SHA-256
`f411b8c800b7147e7196285d37390fc33e1a38af1ea369a5a6f7e7aecb87afcb`), covering
routes, F32 input, expert rows, shared output and combined output. This closes
the fixed-GPU-owner repeatability control for this sampled boundary. The
separate `STMOEX01` execution dump is emitted once per process, so only the
first request's resident weights and Q8_1 bytes were captured; byte identity
of those two fields is not claimed.

Instrumented prompt rates were 87.0 and 87.6 tok/s; 32-token decode rates were
1.2 and 1.3 tok/s. These are repeat diagnostics, not backend performance
comparisons. The deliberately modified profile produced only 12.2% GPU-cache
hits in each request. Supervision recorded 8.72 GiB minimum available memory,
4.13 GiB peak swap and zero cgroup OOM kills. Raw captures and telemetry are
under `/tmp/e6-65k-moe-fixed-gpu-repeat.*` and
`/tmp/e6-65k-moe-fixed-gpu-supervisor/`.

## Fixed-GPU-owner accepted-prefix repeat

The same fixed-GPU setup repeated the 65K prompt twice with 32 generated
tokens and sampled accepted-prefix state at the first, every eighth, and final
committed token. Expert 320 was GPU-owned at the sampled prompt-boundary row
in both requests (`route_kind = 0`). Both requests emitted the same 32 token
IDs; all five sampled commit records matched exactly, including the eleven
persistent-state fingerprints at positions 65,535, 65,542, 65,550, 65,558,
and 65,566. The checker passed. This establishes repeated accepted-prefix
state for this fixed-GPU 65K/32 case, not cross-owner equivalence or general
quality.

Accepted-prefix synchronization made decode tracing intrusive: the 32-token
requests took about 119 seconds to decode, so rates from this run are excluded.
Supervision recorded 8.75 GiB minimum available RAM, 3.41 GiB peak swap and
zero sampled cgroup OOM kills. Raw trace log and supervisor data are under
`/tmp/e6-65k-moe-fixed-gpu-repeat.log` and
`/tmp/e6-65k-moe-fixed-gpu-prefix-supervisor/`.

## Interpretation and limits

This is evidence of request-to-request variation in one expert row with fixed
route IDs and input but different execution owners, reproduced byte-for-byte
under both backend configurations. The output change is explained by the
CPU-miss versus resident-GPU computation path for expert 320. This does not
establish a general determinism guarantee or quantify an end-to-end speedup.
Both fixed-CPU-owner and fixed-GPU-owner repeated-service controls now match
recorded state and MoE outputs exactly for their sampled boundary. Fixed-GPU
accepted-prefix state also repeats exactly over the sampled 65K/32 generation.
The remaining paired owner-mode prefix check is the CPU-owner repeat, followed
by broader quality/repeatability checks and no-trace performance comparisons
that record real residency and hit-rate distributions.

Both requests passed. The initial bundle run recorded 8.61 GiB minimum
available RAM, 4.18 GiB peak swap use, and no cgroup OOM kills. The follow-up
execution capture's resource data is listed above. Full raw bundle, logs,
oracle data, and telemetry remain under `/tmp/e6-65k-ninfer-moe-layer1-capture/`.

# NInfer E7 release assessment

Date: 2026-10-25. Branch: `feat/ninfer-expert-e0`.

## Decision

**No NInfer release profile is proposed.** Keep `--expert-backend ninfer`
experimental and opt-in; the default remains Strata. The bounded CUDA Q2_0 path
is implemented and has run against the Qwen3.8-Flash-Next Q2_0 model on the
Jetson AGX Orin. A corrected 6-GiB staged profile now has a seven-pair TTFT
effect on one short request and passes one held-out exact-answer/state check.
That is narrow workload evidence; performance across the declared contexts and
quality across tasks remain unqualified. This is not a general performance
release.

The implementation outcome is therefore bounded: the selected resident-expert
path, fallback behavior, operator arithmetic and several static-service state
cases have direct evidence. The outcome does not imply support for other
formats, live state migration, or general generation quality. One
workload-specific TTFT effect is confirmed; a general performance-qualified
release profile is **not achieved**.

## Evidence and limits

- The CUDA path is limited to Q2_0 gate/up and Q2_0 down weights with
  Flash-Next 2560/640 geometry. It is guarded by a CUDA build definition. The
  default dispatch remains Strata; strict mode rejects unsupported pairs and
  non-strict NInfer mode falls back.
- The initial packed `dp4a` operator passed grouped parity but remained 4.36×
  slower than Strata on 64/128-token shapes. A later four-entry, 16-lane Q2
  schedule passed exact grouped-output fixtures and reduced those ratios to
  1.107×/1.120×; a specialized one-entry operator measured 0.980×. The
  operator result is still not an end-to-end win. See the
  [E6 grouped throughput report](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/README.md).
- The initial packed-dot and four-entry/single-entry 8K service screens were
  collected before the grouped SwiGLU precision fix. The packed-dot screen's
  median NInfer latency changes were +0.34% prompt, +1.77% decode, +0.82%
  client total and +0.36% TTFT;
  positive values mean slower. Decode was slower in all pairs. The predeclared
  useful-effect gate failed, so seven-pair confirmation was not justified for
  those builds. A subsequent three-pair screen of the
  four-entry/single-entry candidate was also slower: median +2.74% client total
  and +2.70% client TTFT, with NInfer slower in all pairs and outputs/maps
  matching. It did not meet the useful-effect threshold.
- The one-pair context screen from 1K through 256K passed all eligible API and
  exact token-count checks. Minimum available physical/admission memory was
  11.31 GiB; the 6 GiB floor held and all eighteen startup residency maps
  matched. It has no quality oracle and cannot establish a performance effect.
  A corrected-binary 4K/8K rerun also passed all eligible checks, with all
  measured response hashes and residency maps matching. It showed no consistent
  backend advantage. A three-pair repeat of the lone 4K/557-token timing
  outlier did not reproduce it; median TTFT/client changes were −1.08%/−0.67%,
  below the 5% screen threshold. See the [corrected capacity screen](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/fixed-swiglu-context-check/README.md)
  and [outlier repeat](../../bench/results/2026-10-25-phase-e6-q2-557-repeat3/README.md).
  The corrected-binary randomized three-pair 8K screen covered
  five natural-generation shapes and three randomized pairs. All measured
  outputs and resident maps matched; median TTFT changes ranged from −1.59% to
  +0.21%, and no cell met the threshold. One 2,048+128 pair had a 32.6%
  decode-time regression. No seven-pair confirmation was warranted. Its
  [paired-effect chart](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/fixed-swiglu-8k-paired-screen/q2_0-8k-effects.svg)
  includes block values and paired-bootstrap intervals; with three blocks,
  these intervals describe screening uncertainty only. The full [8K report](../../bench/results/2026-10-25-phase-e6-q2-grouped-throughput/fixed-swiglu-8k-paired-screen/README.md)
  has CSV/JSON data and reproduction details.
- The grouped SwiGLU Q8_1 path initially used approximate `__fdividef`, while
  Strata used precise division. On the captured layer-3 expert-94 row this
  changed one Q8_1 code byte despite exact gate/up inputs. Matching Strata's
  expression restored all Q8_1 bytes and grouped expert output in the
  standalone replay. The corrected 512-token retrieval task then returned
  matching token IDs and final persistent-state fields.
- A corrected 6-GiB staged screen measured a median paired TTFT change of
  −6.29% across three pairs. Seven-pair confirmation measured −5.96% with
  paired-bootstrap 95% interval −6.23% to −5.80%. Client completion changed
  −4.17% (interval −4.40% to −4.00%); all measured response and residency-map
  hashes matched. All seven warmup hashes differed across arms. Minimum
  available memory was 11.37 GiB. This confirms the registered TTFT effect
  only for the short measured request; grouped 64/128-token operator timing
  remains slower at 1.098×/1.123×.
- A subsequent balanced three-pair comparison of CPU miss fallback and strict
  NInfer staging at 8K found a 1,069-token cell with median +7.04% prompt TPS,
  +8.54% decode TPS, −6.56% TTFT and −7.60% client time. Its measured output
  hash differed in all three pairs. The 557-token cell also differed in every
  pair, despite a +7.99% median decode-TPS change; TTFT changed only +0.21% and
  client time −2.54%. A separate capture reproduced the 1,069-token divergence
  and found a warmup/measured-output difference in the CPU-miss arm. Since no
  independent task-quality oracle or causal explanation is available, these
  are exploratory timings and no seven-pair confirmation was run. See the
  [staged workload report](../../bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/README.md).
- A randomized three-pair service screen compared Strata and strict NInfer
  while both used the staged route on the 2K retrieval. Median paired decode
  rate changed 0.00%; NInfer won one of three pairs, so the preregistered 5%
  primary gate failed and no confirmation was run. A layer-1 captured-activation
  check found no CPU/CUDA Q8_1 scale or code mismatch for either route
  independently. An independent direct comparison also found identical Q8_1
  scales and codes for all 80 blocks across the slightly different layer-1
  vectors (relative L2 `1.027e-7`). At sampled layer 2, 34 of 80 activation
  scales and 103 Q8_1 code values differed; later sampled layers showed more
  differences. This places the first sampled activation-code divergence at
  layer 2, but its upstream cause remains unknown. Together with CPU-miss/staged state
  differences observed through 64K, staged expert misses remain outside a
  proposed release profile. See the [staged-backend performance screen](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/performance-staged-backend-screen/README.md)
  and [captured Q8_1 diagnostic](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/q8_1-capture-check/README.md).
- E5 includes operator and state checks for the bounded static Q2_0 profile.
  Pre-fix natural-generation and 4K retrieval state differences were rerun
  after the SwiGLU precision fix: two natural-generation runs and one 4K
  retrieval comparison matched token IDs and all final state fields. This
  resolves those specific cases, but broader task quality and numerical bounds
  remain open. An additional held-out 8,192-token retrieval/arithmetic check
  returned the exact answer on both Strata and strict NInfer, with all token
  IDs and nine final state fields matching; minimum available memory was
  17.70 GiB. This is one task at one prompt length. See the [8K check](../../bench/results/2026-10-25-phase-e5-q2-ninfer-8k-retrieval/README.md),
  and the same task at 16K also matched answer, token IDs and all nine state
  fields, with 17.09 GiB minimum available memory. Both runs are single-task
  functional checks, not long-context performance estimates. See the [16K
  check](../../bench/results/2026-10-25-phase-e5-q2-ninfer-16k-retrieval/README.md),
  and the same retrieval also passed at an actual 32,768-token prompt under a
  64K cap, with exact token and final-state parity and 16.48 GiB minimum
  availability. The same task passed at an actual 65,536-token prompt under a
  128K cap, with 14.70 GiB minimum availability; near-limit 128K ingestion
  remains untested. See the [32K
  check](../../bench/results/2026-10-25-phase-e5-q2-ninfer-32k-retrieval/README.md)
  and [64K check](../../bench/results/2026-10-25-phase-e5-q2-ninfer-64k-retrieval/README.md),
  and the same actual retrieval at 131,072 tokens under a 256K cap, with exact
  answer/token/state parity and 11.40 GiB minimum available memory. This is
  still one task. A 240,286-token retrieval under a 262,144-token cap also
  returned the exact answer with matching token IDs and all nine final state
  fields; minimum available memory was 11.44 GiB. Its successful retry used an
  experiment-only 300-second watchdog allowance after a previous 60-second
  timeout. This single functional case does not establish broader near-limit
  quality or performance. See the [128K check](../../bench/results/2026-10-25-phase-e5-q2-ninfer-128k-retrieval/README.md)
  and [240K check](../../bench/results/2026-10-25-phase-e5-q2-ninfer-240k-retrieval/README.md),
  [E5 closeout](NINFER_E5_CLOSEOUT.md) and the
  [corrected generation checks](../../bench/results/2026-10-25-phase-e5-q2-ninfer-generation-regression/fixed-kernel/README.md).
- Coder IQ1_M, ISTA-DASLab IQ3_S, staged expert misses, broad task quality and
  live Strata/NInfer state migration are not supported or qualified by this
  release assessment.

## Build evidence

On the local Jetson AGX Orin, `cmake --build
build/integration/e0-cuda-build --parallel 2` completed successfully, as did
the explicit `strata` and `ninfer_q2_expert_parity` target check. The build
configuration has CUDA enabled and HIP/SYCL disabled. The rebuilt server's
`--help` output reports the limited Q2_0 geometry and strict/fallback behavior.
Binary SHA256 values:

| Artifact | SHA256 |
| --- | --- |
| `strata` | `c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75` |
| `ninfer_q2_expert_parity` | `ec1d713c80aaeb266a8b4934d73faef8bac08692349b2d39db7f09c075811602` |

Current-source HIP and SYCL builds have now passed on `maestro1`, using its
mounted `/mnt/sda2` scratch volume and toolchains outside the login PATH. The
build source was exact commit `1f9f116b181ef0503f4203f26922b90e213d4615`.
HIP used ROCm HIP 7.2.53210 / AMD Clang 22.0.0 with `gfx1100`; SYCL used Intel
oneAPI DPC++/C++ 2026.1.1. Both Release builds used bounded parallelism 2,
linked the `strata` target, and passed a model-free `strata --help` invocation.
The SYCL build completed all 201 steps. Binary hashes, configure metadata and
full logs are in the [maestro1 current-source build report](../../bench/results/2026-10-26-e7-maestro-current-source-builds/README.md).
These are x86_64 build and CLI-startup results only. maestro1 has an Intel HD
Graphics 500, so this is not HIP/SYCL device execution, backend correctness,
or Orin performance evidence. The NInfer expert kernels remain CUDA-only and
no general NInfer release profile is proposed.

## Sustained service and next entry criteria

No 30-minute NInfer soak was started because no general release profile is
proposed. Existing Strata services, clocks and system configuration were left
alone. E7 remains open for broader task-quality checks on the corrected
binary, context/model coverage, backend build evidence and a proposed profile
that passes those gates. The corrected request-level result is faster on the
measured short request, but the grouped 64/128-token operator is still slower.
The 30-minute soak requirement remains untriggered.

## Current state-hash source backend build follow-up

The backend builds were repeated at exact commit
`68de59ab2c6736ca328c83afabe2138123cd7051`. HIP build and `strata --help`
passed. SYCL compile/link passed after sourcing oneMKL so `MKLROOT` was set;
the host exposes no SYCL platform, so CLI startup aborted with “No device of
requested type available.” This is build evidence only for the new SYCL binary.
The earlier commit's SYCL help result does not establish startup on this newer
binary. Full hashes and setup notes are in the [maestro1 build report](../../bench/results/2026-10-26-e7-maestro-current-source-builds/README.md#2026-10-26-follow-up-on-state-diagnostic-source).

## Staged-miss state-parity follow-up (2026-10-26)

A held-out 2,048-token retrieval task passed its exact answer and token-ID
checks on CPU-miss and strict NInfer staged routes, with matching startup
residency maps. The final accepted-prefix state still differed in six fields,
and the GDN arrays differed by 3.41% global relative L2. A resident-only
Strata/NInfer control matched all final state fields and the full GDN arrays.
This isolates the unresolved result to the staged-miss configuration for this
task; it does not establish a general cause or release profile. E7 remains
open. See the [held-out retrieval/state report](../../bench/results/2026-10-26-e6-q2-staged-retrieval-2k/README.md).

The same held-out exact-answer retrieval/arithmetic task also passed answer and
token-ID checks at 4K, 8K, 16K and 32K prompts with identical startup residency
maps. Final state hashes differed at all lengths. Numeric GDN comparisons
measured 2.645%, 3.159%, 2.572% and 2.685% global relative L2 at 4K, 8K, 16K
and 32K over 29.4M floats; these values are not monotonic with prompt length.
Minimum available memory was 9.93 GiB at 32K. This broadens one task's length
coverage but does not bound general generation quality or establish an
approximate-state contract. The five-shape replay still had output-hash
mismatches, so no staged release profile or performance claim is proposed. See
the [4K–32K follow-up](../../bench/results/2026-10-26-e6-staged-retrieval-context-followup/README.md).

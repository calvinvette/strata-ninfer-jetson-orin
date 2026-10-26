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
- E5 includes operator and state checks for the bounded static Q2_0 profile.
  Pre-fix natural-generation and 4K retrieval state differences were rerun
  after the SwiGLU precision fix: two natural-generation runs and one 4K
  retrieval comparison matched token IDs and all final state fields. This
  resolves those specific cases, but broader task quality and numerical bounds
  remain open. An additional held-out 8,192-token retrieval/arithmetic check
  returned the exact answer on both Strata and strict NInfer, with all token
  IDs and nine final state fields matching; minimum available memory was
  17.70 GiB. This is one task at one prompt length. See the [8K check](../../bench/results/2026-10-25-phase-e5-q2-ninfer-8k-retrieval/README.md),
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

HIP and SYCL builds remain unverified. Neither compiler was available on the
Orin or on `maestro1`; the latter had 1.1 GiB free on its root filesystem and
no HIP/SYCL compiler in PATH or under `/opt`. No storage was removed to make
space. The NInfer kernel itself is CUDA-only and the HIP/SYCL source sets remain
unchanged, but the shared-file build requirement has not been met for those
backends.

## Sustained service and next entry criteria

No 30-minute NInfer soak was started because no general release profile is
proposed. Existing Strata services, clocks and system configuration were left
alone. E7 remains open for broader task-quality checks on the corrected
binary, context/model coverage, backend build evidence and a proposed profile
that passes those gates. The corrected request-level result is faster on the
measured short request, but the grouped 64/128-token operator is still slower.
The 30-minute soak requirement remains untriggered.

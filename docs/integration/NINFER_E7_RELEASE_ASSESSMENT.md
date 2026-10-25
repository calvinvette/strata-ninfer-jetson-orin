# NInfer E7 release assessment

Date: 2026-10-25. Branch: `feat/ninfer-expert-e0`.

## Decision

**No NInfer release profile is proposed.** Keep `--expert-backend ninfer`
experimental and opt-in; the default remains Strata. The bounded CUDA Q2_0 path
is implemented and has run against the Qwen3.8-Flash-Next Q2_0 model on the
Jetson AGX Orin, but the performance gate failed and model-level quality is not
qualified across tasks. This is not a performance release.

The implementation outcome is therefore bounded: the selected resident-expert
path, fallback behavior, operator arithmetic and several static-service state
cases have direct evidence. The outcome does not imply support for other
formats, staged misses, live state migration, or general generation quality.
The separate performance-qualified outcome is **not achieved**.

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
- The first same-day three-pair 8K service screen measured median NInfer latency
  changes of +0.34% prompt, +1.77% decode, +0.82% client total and +0.36% TTFT;
  positive values mean slower. Decode was slower in all pairs. The predeclared
  useful-effect gate failed, so seven-pair confirmation and performance charts
  with uncertainty were not justified. A subsequent three-pair screen of the
  four-entry/single-entry candidate was also slower: median +2.74% client total
  and +2.70% client TTFT, with NInfer slower in all pairs and outputs/maps
  matching. It did not meet the useful-effect threshold.
- The one-pair context screen from 1K through 256K passed all eligible API and
  exact token-count checks. Minimum available physical/admission memory was
  11.31 GiB; the 6 GiB floor held and all eighteen startup residency maps
  matched. It has no quality oracle and cannot establish a performance effect.
- E5 includes operator and state checks for the bounded static Q2_0 profile.
  However, a 512-token natural-generation comparison first differed at
  generated token 9, a 4K retrieval comparison had different persistent-state
  fingerprints, and a backend capture found numerical state drift. These
  observations do not prove a quality failure, but they leave task-level
  equivalence unresolved. See the [E5 closeout](NINFER_E5_CLOSEOUT.md).
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
| `strata` | `daaf67ff7b764f0bd8413bee1d4e027132d4f2f978472795a82404fddeb5d420` |
| `ninfer_q2_expert_parity` | `6334fb6015e115ea8978f870aa6e25a2cb122761fd098a23a318b3bc1e1fd2bb` |

HIP and SYCL builds remain unverified. Neither compiler was available on the
Orin or on `maestro1`; the latter had 1.1 GiB free on its root filesystem and
no HIP/SYCL compiler in PATH or under `/opt`. No storage was removed to make
space. The NInfer kernel itself is CUDA-only and the HIP/SYCL source sets remain
unchanged, but the shared-file build requirement has not been met for those
backends.

## Sustained service and next entry criteria

No 30-minute NInfer soak was started: there is no proposed release profile
after the failed useful-effect screen, and a soak would not change the release
decision. Existing Strata services, clocks and system configuration were left
alone. E7 release qualification remains open until a candidate both passes the
performance and task-quality gates and receives the required builds and
sustained-service checks. Any renewed work should first change the operator or
request critical path, then repeat same-day paired controls before proposing a
profile. The latest one-entry operator matches Strata within this harness, but
the request-level screen remains slower; no profile is nominated. The 30-minute
soak requirement remains untriggered.

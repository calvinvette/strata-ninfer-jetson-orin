# E6 Q2_0 grouped expert throughput screen

Date: 2026-10-25. Jetson AGX Orin, CUDA 12.6, SM87. This is a diagnostic
operator screen for the NInfer-derived Q2_0 path, not natural-request
performance or a release qualification.

## Workload and identity

The harness used layer 0, expert 32 from the Coder Q2_0 GGUF, with a captured
layer-0 activation fixture (SHA256
`607553ddddee20523c8259ba171eedc35fb01239dca19d1124114cf574515391`). The
fixture originated from the Phase 5 activation-error report and is not claimed
to be this Q2_0 model's own activation distribution. Timing transforms that one
input into a 64- or 128-token diagnostic batch, routes each token to ten
experts, and runs the grouped gate/up, SwiGLU/Q8_1 and down path. Weights,
routes, activation buffers and workspaces are resident and prepared before
timing. No model loading, routing, transfer, staging, service, or dense-layer
work is included.

The source artifact was
`Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` under
`~/models/strata-orin-validation/Q2_0/`. The parity reference fixture SHA256
was `86630939911b8899265cc806fefc448ce462f32958c13a150af84936fc604c9a`.
The packed-dot timing harness binary had SHA256
`1a0618419eb05e008dd7c480836694fde3c8d55a6e94170dfe2de2b8cb10dd1c`.

## Results

| Revision / tokens × top-10 entries | Strata median | NInfer median | NInfer / Strata | Correctness |
| --- | ---: | ---: | ---: | --- |
| Scalar D3/D4, 64 × 640 | 3,945.5 µs | 48,054.1 µs | 12.18× latency | relative L1 `9.33e-8`, pass |
| Scalar D3/D4, 128 × 1,280 | 7,954.5 µs | 98,105.9 µs | 12.31× latency | relative L1 `9.32e-8`, pass |
| Packed `dp4a`, 64 × 640 | 3,945.9 µs | 17,226.0 µs | 4.36× latency | relative L1 `1.85e-5`, pass |
| Packed `dp4a`, 128 × 1,280 | 7,956.6 µs | 34,692.4 µs | 4.36× latency | relative L1 `1.86e-5`, pass |
| Packed `dp4a`, one resident entry | 24.48 µs | 44.71 µs | 1.83× latency | relative L1 `8.30e-8`, pass |

Each timing is the median of seven interleaved paired blocks, 50 invocations per
arm per block. For packed `dp4a`, observed min/max were 3,942.9–3,953.3 /
17,219.1–17,343.5 µs at 64 tokens and 7,950.7–7,960.2 / 34,681.1–34,702.5 µs
at 128 tokens (Strata / NInfer). The model-derived D3/D4 FP64 parity check
passed with relative L2 `2.13e-7`; no output entries were unwritten. An
eight-rows-per-CTA trial passed after correcting its row stride but was slower
(4.47× / 4.48×), so it was not retained. The initial row-stride attempt failed
with 1,280 single-token outputs and 816,640 64-token outputs unwritten due to a
host launch/kernel row-stride mismatch; the corrected retry passed. These are
diagnostic tuning cells, not release results.

The initial NInfer implementation launched SwiGLU/Q8_1 quantization once per
eight entries. A CUDA-side equivalent that processes all entries in one launch
was added and passed grouped-output parity. It changed the grouped ratio only
from 12.27× to 12.18× at 64 tokens and from 12.39× to 12.31× at 128 tokens,
so launch count in this stage was not the main cost.

An Nsight Systems diagnostic capture of the scalar path found the grouped
NInfer Q2 D3/D4 kernels dominated device time. Across the captured harness,
their median kernel durations were 48.4 and 32.8 µs; Strata's Q2-specialized
gate/up and down kernels were 9.4 and 9.3 µs. The NInfer kernels decode Q2
values in scalar loops, while Strata uses packed integer-dot operations. The
capture contains parity and repeated timing calls and is not used for the
paired medians above. Adapting the grouped D3/D4 inner loop to packed signed
byte `dp4a` reduced operator latency by about 64% while preserving the
route/output interface. The trace is retained locally at
`/tmp/ninfer-q2-grouped-optimized.nsys-rep`; only its summary is recorded here.

## Resources and interpretation

Runs used the repository's `run_control.py` supervisor with the existing 6 GiB
floor, read-only clock sampling and no clock controls. The packed-dot unprofiled
run lasted 26.4 seconds; minimum available physical memory was 26,801,688,576
bytes (about 25.0 GiB). GPU frequency was observed at 306 MHz; EMC readback was
denied, and energy was not attributed.

A same-day three-pair service screen after the packed-dot build used the same
8K Q2_0 profile and identical 3,000-entry resident-map hash in all six runs;
all six responses had text SHA256
`18e649c52e8a6a942bfb6c486a4da267fc7ca05faaf55c831ea4b35372df848e`.

| Paired service screen (NInfer / Strata) | Prompt ms | Decode ms | Client total s | TTFT s |
| --- | ---: | ---: | ---: | ---: |
| Pair 1 | 6,174 / 5,835 | 3,235 / 3,126 | 9.413 / 8.964 | 6.260 / 5.921 |
| Pair 2 | 5,900 / 5,880 | 3,165 / 3,110 | 9.067 / 8.994 | 5.985 / 5.963 |
| Pair 3 | 5,793 / 5,983 | 3,180 / 3,126 | 8.976 / 9.112 | 5.878 / 6.068 |

Median paired NInfer latency changes
were +0.34% prompt, +1.77% decode, +0.82% client total and +0.36% TTFT (positive
means slower). Decode was slower in all three pairs. This is a small screening
set, not a performance estimate, and does not justify seven-pair confirmation.
The service binary SHA256 was
`ef3da9e05acc8cd6ebc24ecf3de09fe293f3f458a93574516f85880f2d0f1316`. The
supervised campaign lasted 258.9 seconds and minimum available memory was
19,116,306,432 bytes (about 17.8 GiB), above the 6 GiB floor. Because this
revision still fails the operator and useful-service gates, broader
context-size service measurements are deferred until a materially faster
candidate passes a new screen.

## Reproduction

```sh
python3 tools/integration/run_control.py \
  --output <supervisor-output> --timeout 180 --interval 1 --sample-clocks -- \
  build/integration/e0-cuda-build/ninfer_q2_expert_parity \
  ~/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
  0 32 \
  bench/results/2026-10-15-phase5-activation-error-decomposition/weights-and-outputs/layer-0-expert-32-activation.f32 \
  <independent-fp64-reference> <output-fixture>
```

The harness prints parity and the per-shape paired timing screen. The service
screen can be rerun with
`python3 bench/results/2026-10-25-phase-e6-q2-grouped-throughput/run_service_paired_screen.py`.
Raw supervisor telemetry and generated outputs remain outside this report.

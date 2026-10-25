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
The timing harness binary after the grouped quantizer change had SHA256
`3d1dfca72dfec8dd928fcd494ec269726526b7aedc2182e54f7149e30d399493`.

## Results

| Tokens × top-10 entries | Strata median | NInfer median | NInfer / Strata | Correctness |
| ---: | ---: | ---: | ---: | --- |
| 64 × 640 | 3,945.5 µs | 48,054.1 µs | 12.18× latency | grouped relative L1 `9.33e-8`, pass |
| 128 × 1,280 | 7,954.5 µs | 98,105.9 µs | 12.31× latency | grouped relative L1 `9.32e-8`, pass |

Each timing is the median of seven interleaved paired blocks, 50 invocations per
arm per block. The observed min/max were 3,943.5–3,951.7 / 48,043.8–48,223.7
µs at 64 tokens and 7,952.0–7,988.2 / 97,920.5–98,302.9 µs at 128 tokens
(Strata / NInfer). The model-derived D3/D4 parity check also passed with
relative L2 `2.13e-7`; no output entries were unwritten.

The initial NInfer implementation launched SwiGLU/Q8_1 quantization once per
eight entries. A CUDA-side equivalent that processes all entries in one launch
was added and passed grouped-output parity. It changed the grouped ratio only
from 12.27× to 12.18× at 64 tokens and from 12.39× to 12.31× at 128 tokens,
so launch count in this stage was not the main cost.

An Nsight Systems diagnostic capture of the optimized path found the grouped
NInfer Q2 D3/D4 kernels dominated device time. Across the captured harness,
their median kernel durations were 48.4 and 32.8 µs; Strata's Q2-specialized
gate/up and down kernels were 9.4 and 9.3 µs. The NInfer kernels decode Q2
values in scalar loops, while Strata uses packed integer-dot operations. The
capture contains parity and repeated timing calls and is not used for the
paired medians above. The trace is retained locally at
`/tmp/ninfer-q2-grouped-optimized.nsys-rep`; only its summary is recorded here.

## Resources and interpretation

Runs used the repository's `run_control.py` supervisor with the existing 6 GiB
floor, read-only clock sampling and no clock controls. The optimized unprofiled
run lasted 63.3 seconds; minimum available physical memory was 25,936,175,104
bytes (about 24.2 GiB). GPU frequency was observed at 306 MHz at samples;
frequencies remained dynamically managed. EMC readback was denied, and energy
was not attributed. This is a clear negative operator screen for the current
NInfer Q2 schedule; it does not estimate end-to-end impact, which is separately
negative in the three-pair E2 service screen. Do not run seven-pair
confirmation for this revision. A candidate that replaces the scalar Q2 dot
schedule with a packed integer-dot implementation would need fresh parity and
screening before any broader context matrix or confirmation campaign.

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

The harness prints parity and the per-shape paired timing screen. Raw
supervisor telemetry and generated outputs remain outside the curated report.

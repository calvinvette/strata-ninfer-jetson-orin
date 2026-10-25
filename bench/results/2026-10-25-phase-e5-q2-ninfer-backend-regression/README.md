# E5 Q2_0 Strata-versus-NInfer state comparison

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. The comparison used
the same Q2_0 model, PLE pack, tokenizer, expert profile, 512-token retrieval
prompt, cache, prefill chunk, worker count, KV format and MTP-off setting. The
only engine option changed was the expert backend: default Strata versus strict
NInfer. Both were fresh sequential services. The Release binary SHA256 was
`527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`.

## End-to-end output and persistent state

Both backends returned the exact expected retrieval/arithmetic answer in 47
tokens, with identical token IDs. The final persistent state was not equal:
GDN, tail, pooled, full pooled and KV fingerprints differed, while PLE, dead
slots and previous PLE tokens matched.

The GDN arrays were compared directly at the first committed token (`L=512`)
and after the full response (`L=558`):

| Boundary | Different GDN values | Global relative L2 | RMS absolute delta | Maximum absolute delta |
| --- | ---: | ---: | ---: | ---: |
| First committed token | 94.43% | 0.09019 | 0.02403 | 16.7992 |
| Final response | 95.60% | 0.03367 | 0.00841 | 0.99831 |

At the first-token boundary, the maximum per-layer relative L2 was 0.22494 at
GDN layer 33. At the final boundary it was 0.06992 at GDN layer 25. The raw
113-MB-per-arm GDN arrays remain local and are not committed; the streamed
numeric analyses and full token/state results are retained under `evidence/`.

## Captured verifier trace

At the prompt's final token position (511), opt-in route, input, per-expert
parts and combined-output captures were collected at model layers 0, 1 and 2.
Route IDs were identical at all three layers.

| Model layer | Input relative L2 | Expert-parts relative L2 | Combined-output relative L2 | Notes |
| ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 0 | 0 | Inputs, routes, expert parts and outputs bit-identical. |
| 1 | 0 | 2.94e-8 | 5.54e-8 | Same routes and weights; first captured numeric difference is in expert parts. |
| 2 | 7.25e-4 | 7.84e-3 | 5.78e-3 | Same expert IDs; maximum route-weight delta 4.27e-5. |

This locates a tiny per-expert arithmetic difference at layer 1, followed by
larger activation and expert-output differences by layer 2. It does not identify
the operation that amplifies the difference or establish a general output
quality bound. The one-token and full-task result JSON, direct GDN metrics and
compact layer captures are in [`evidence/`](evidence/). The reproducible layer
capture analyzer is
[`analyze_ninfer_backend_capture.py`](../../../tools/integration/analyze_ninfer_backend_capture.py).

## Resource scope and decision

Each supervised comparison/capture stayed above 17.78 GiB minimum physical and
admission availability, above the 6 GiB headroom floor, with no sampled cgroup
memory events. The exact-answer checks passed, while the strict state-parity
check correctly failed. These one-prompt observations do not prove a general
quality regression, but the measured state movement is too large to classify as
hash-only noise. E5 therefore remains open for a declared state/numerical
acceptance bound and broader output quality evidence. Keep the backend opt-in
and isolate it to fresh sessions; do not switch an in-flight session between
Strata and NInfer based on text parity alone.

The first GDN dump attempt used the maximum generation allowance as its target,
but the task naturally stopped one token earlier; the attempt is retained in
the local raw run. The corrected capture used the observed accepted length.

# First verifier-window state hashes by layer

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is an instrumented,
same-process state diagnostic, not a performance or quality result.

## Setup

One current-source strict-NInfer process handled the identical 65,536-token
prompt twice, with temperature 0, 32-token generation limit and 131,072-token
context. Prompt cache and PCIe staging were disabled. The CUDA executable SHA
was `91314049e2ce76215f474dceaef43d2094f6b2fb2bb8e125fbb197d0ec30c4d8`.
The opt-in no-trace captures included immediate reset state, a compact
pre-verifier capture at position 65,535, the prompt-boundary fingerprint, and
per-layer GDN/QSA hashes from the existing state-hash diagnostics.

## Result

Both requests passed. The pre-verifier capture at position 65,535 matched,
as in the [final prompt-token transition report](final-prompt-token-verifier-transition.md).
Immediately after the first one-token verifier window, 36 ordered GDN state
hashes and 12 QSA layer hashes were emitted for each request.

| Ordered GDN state ordinal | Model layer | Request 1 | Request 2 | Match |
| ---: | ---: | --- | --- | --- |
| 0 | 0 | `e69dda615ebd4d79` | `e69dda615ebd4d79` | Yes |
| 1 | 1 | `9764954a90616b52` | `9764954a90616b52` | Yes |
| 2 | 2 | `08daea3b8a39b141` | `a292de99ce639cbe` | No |
| 3 | 4 | `b2f91cddca51a9ec` | `95daa7c9ef77502b` | No |

The first divergent recurrent-state hash is ordinal 2, corresponding to model
layer 2. The mapping follows the model’s ordered layers: QSA is on model layers
3, 7, 11, …, 47, while GDN state hashes cover the intervening layers.

The first QSA layer, model layer 3, also differed:

| QSA field | Request 1 | Request 2 |
| --- | --- | --- |
| Combined layer hash | `6e0ee47874e74053` | `d9645837ee0ca378` |
| Index hash | `2f28bf1bbca8da38` | `6bc6ac305d6c5d90` |
| KV hash | `fd26375575fc1af8` | `33daced773d34b8b` |

All 12 QSA layer combined/index/KV hashes differed. GDN ordinals 0 and 1
matched, so layer 2 is the first observed divergent model layer; later GDN and
QSA differences are downstream in this execution order. The response hashes
were `9eb4258bd7960b7d229788732574e77e3d1de986c5ac8c1a071e5a97521f9101` and
`aa244120f27dce23fbd847125de7ca2347e6c0ad9e3bd8f3cee49cf447ce96c9`.

## Interpretation and limits

This localizes the first persistent recurrent-state mismatch to model layer 2
of the one-token verifier window that consumes prompt token 65,535. The first
QSA mismatch at model layer 3 follows it. The hashes do not identify whether
layer 2 receives differing activations, makes a nondeterministic numerical
choice, or writes divergent state from another cause. Next capture layer 2’s
pre/post GDN state and relevant verifier activation for the same window.

State hashing synchronizes and copies device data and may perturb scheduling.
The 65K prompts took about 13 minutes each; those timings are diagnostic only.
Energy and continuous clocks were not collected. E6/E7 remain open.

Raw logs and response bodies remain under
`/tmp/e6-65k-ninfer-verifier-layer-hashes/`.

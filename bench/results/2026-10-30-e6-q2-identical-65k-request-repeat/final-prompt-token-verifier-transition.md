# State transition at the final prompt-token verifier window

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is an instrumented,
same-process state diagnostic, not a performance or quality result.

## Setup

One current-source strict-NInfer process handled two identical requests using
the same 65,536-token prompt, temperature 0, 32-token generation limit and
131,072-token context. Prompt cache and PCIe staging were disabled. The CUDA
executable SHA-256 was
`91314049e2ce76215f474dceaef43d2094f6b2fb2bb8e125fbb197d0ec30c4d8` (source
commit `3776d75d`). Compact request-state captures were taken after prefill at
53,248, 57,344, 61,440 and 65,535. The existing prompt-boundary fingerprint
runs immediately after the verifier processes the final prompt token.

## Result

Both requests passed and reported 65,536 prompt tokens and 32 generated tokens.
The immediate post-reset state and all four prefill captures matched exactly.
The matching prefill fingerprints at each sampled position were:

| Prompt position | GDN | PLE | QSA tail | QSA dead | QSA pooled index state | PLE previous tokens |
| ---: | --- | --- | --- | --- | --- | --- |
| 53,248 | `43a5c1cf47f92334` | `6856faead93bf59c` | `077a0026ea836d09` | `ba4d730b89d297e5` | `abe1302b5439428c` | `2438,2438` |
| 57,344 | `ba4b3e6ece0bd12e` | `b3a0b50b09c26f2d` | `9d954e8cd5f7899e` | `ba4d730b89d297e5` | `37cd2f13e356b95e` | `2438,2438` |
| 61,440 | `974c5de016552d33` | `8784648768985577` | `14704e23993a3be2` | `ba4d730b89d297e5` | `90f1baee22fb9a4a` | `2438,2438` |
| 65,535 | `cbf4deefec5b8210` | `c6a7bc535af8f9a8` | `7b1a170e21f8665b` | `ba4d730b89d297e5` | `baf415a1ca99dde6` | `271,248069` |

At position 65,535, after prefill has consumed token indices `[0, 65,535)` and
before the verifier consumes the final prompt token, both requests had:

| Field | Both requests |
| --- | --- |
| GDN | `cbf4deefec5b8210` |
| PLE | `c6a7bc535af8f9a8` |
| QSA tail | `7b1a170e21f8665b` |
| QSA dead | `ba4d730b89d297e5` |
| QSA pooled index state | `baf415a1ca99dde6` |
| PLE previous tokens | `271,248069` |

Immediately after the first verifier window (`p=65,535`, `T=1`) consumed that
last prompt token, the prompt-boundary fingerprint differed:

| State field | Request 1 | Request 2 | Match |
| --- | --- | --- | --- |
| GDN | `85907b6a2b85d24e` | `5c793b8a70da9a04` | No |
| PLE | `df3795d240365f69` | `df3795d240365f69` | Yes |
| Tail | `c4a5d96bb5c4e077` | `c4a5d96bb5c4e077` | Yes |
| Pooled | `daf9928c718c7b33` | `768df0029b886add` | No |
| KV | `0552810263e21418` | `a9df73b118768bd5` | No |
| MTP | `14650fb0739d0383` | `14650fb0739d0383` | Yes |
| Stale | `14650fb0739d0383` | `14650fb0739d0383` | Yes |
| Dead | `40ccf57e6c30218e` | `40ccf57e6c30218e` | Yes |
| Pooled full | `f2e8d94d3fe3944a` | `ed5187a71d99941c` | No |
| PLE previous tokens | `271,248069` | `271,248069` | Yes |

The response SHA-256 values were `9eb4258bd7960b7d229788732574e77e3d1de986c5ac8c1a071e5a97521f9101`
and `aa244120f27dce23fbd847125de7ca2347e6c0ad9e3bd8f3cee49cf447ce96c9`.

## Interpretation and limits

The compact prefill-state capture matches between requests through the full
prefill range, including the state immediately before the final prompt token
is verified. The first observed difference is immediately after the
single-token verifier window processes that final prompt token. This localizes
the transition to that verifier window and its synchronous state publication
before any generated-token commit. It does not identify which operator or
which arithmetic difference causes the state change. The compact prefill and
prompt-boundary hooks fingerprint different state views; conclusions rely on
within-hook equality across requests, not equality of the printed hash values
between hooks.

Both hooks synchronize and copy state, so they may perturb execution. Prompt
throughput was 86.5 and 86.8 tokens/s in this diagnostic and is not a
performance result. Continuous clocks, energy and memory telemetry were not
collected. E6/E7 remain open.

Raw logs and response bodies remain under
`/tmp/e6-65k-ninfer-prefill-fine/`.

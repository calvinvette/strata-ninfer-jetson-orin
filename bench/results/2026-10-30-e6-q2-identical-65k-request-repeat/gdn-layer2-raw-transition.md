# Raw GDN layer-2 transition at the final prompt token

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is a same-process,
instrumented correctness/localization diagnostic, not a performance result.

## Setup

One strict-NInfer process handled the identical 65,536-token request twice at
temperature 0, with a 32-token generation limit and 131,072-token context.
Prompt cache and PCIe staging were disabled. The same verifier window at
position 65,535 (one token) was captured for model GDN layer 2, including its
input and intermediate tensors, raw GDN output, and pre/post recurrent and
convolution state. The compiled executable SHA was
`91314049e2ce76215f474dceaef43d2094f6b2fb2bb8e125fbb197d0ec30c4d8`.

## Findings

The recurrent matrix and convolution history entering layer 2 were exactly
equal between requests (786,432 and 30,720 float values respectively). The
layer-2 input activation `x` was already slightly different: 2,554/2,560
values, maximum absolute difference `5.14984e-05`, relative L2 `3.10649e-05`.
Thus layer 2 did not begin with identical inputs even though its pre-state was
identical.

| Captured field | Differing values | Maximum absolute difference | Relative L2 |
| --- | ---: | ---: | ---: |
| x | 2,554 / 2,560 | 5.14984e-05 | 3.10649e-05 |
| qkv | 10,237 / 10,240 | 0.00182521 | 3.23708e-04 |
| h | 10,223 / 10,240 | 9.93758e-05 | 1.71064e-04 |
| gate | 47 / 48 | 6.19888e-05 | 1.52651e-05 |
| beta | 48 / 48 | 9.35793e-06 | 4.42820e-06 |
| z | 6,139 / 6,144 | 0.00179267 | 1.92205e-04 |
| y | 6,138 / 6,144 | 0.000283673 | 3.32104e-04 |
| gdn_out | 2,559 / 2,560 | 0.00135808 | 2.32976e-03 |
| ffn_x | 2,560 / 2,560 | 0.00361222 | 9.28428e-04 |
| ffn_y | 2,560 / 2,560 | 0.00114406 | 9.88508e-03 |
| raw GDN recurrence output | 6,139 / 6,144 | 1.95205e-05 | 1.25249e-04 |

After the window, 784,908/786,432 recurrent matrix values differed (maximum
absolute difference `1.5363e-05`, relative L2 `5.5023e-05`); 10,237/30,720
convolution-history values differed (maximum `0.0018252`, relative L2
`1.91276e-04`). This agrees with the first layer-2 state-hash mismatch in the
[per-layer hash report](verifier-first-layer-state-hashes.md).

## Interpretation and limits

The transition is consistent with a small activation difference entering
layer 2, followed by differences through its projections and recurrent update.
It does not show that layer 2 originates the activation difference, nor does
it identify whether the difference arose in layer 1's output/residual path or
earlier. The next useful boundary is the model-layer-1 output/residual feeding
layer 2. Capture synchronization and device copies can perturb scheduling, so
these numbers are diagnostic only. The full raw captures, engine logs, and
comparison JSON remain in `/tmp/e6-65k-ninfer-gdn-layer2-capture/`.

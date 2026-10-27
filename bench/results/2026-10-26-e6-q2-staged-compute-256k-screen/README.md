# E6 Q2_0 staged-compute screen at 256K capacity

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

This was a randomized three-pair screen of Strata grouped compute against strict NInfer grouped compute. Both used the same staged resident map (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`) and `pcie-frac=1`. The configured context capacity was 262,144 tokens; the request itself was only 2,048 prompt + 128 generated tokens, so this tests large-capacity allocation behavior, not long-context throughput or quality. The model/profile was Qwen3.8-Flash-Next GSQ-RCO Q2_0, 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Measured output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | +1.57% | 0.00% | −0.80% | −1.09% | Match | 7.14 / 7.39 GiB |
| 2 | NInfer → Strata | +8.86% | +4.11% | −8.01% | −7.22% | Match | 7.35 / 7.16 GiB |
| 3 | Strata → NInfer | −0.80% | −29.73% | +0.74% | +10.67% | **Mismatch** | 7.34 / 7.16 GiB |
| Median paired change |  | **+1.57%** | **0.00%** | **−0.80%** | **−1.09%** | 2/3 match |  |

All three arms completed without a failed supervisor or crossing the 6-GiB available-memory floor. The paired medians do not meet the pre-registered 5% gain screen, and pair 3 is not a quality pass: NInfer emitted SHA-256 `753ec32d…`, while Strata emitted `a868c120…`. Its NInfer decode time was 24.52 s versus 17.25 s for Strata. Do not interpret the median as a qualified speedup.

A separate one-pair rerun with text capture produced identical measured Strata and NInfer outputs (`a868c120…`), although the Strata warmup output differed. This shows that the mismatch was not reproduced in that diagnostic; it does not establish why pair 3 diverged or invalidate it. Clock observations were dynamic (306–1300.5 MHz); EMC readback was unavailable and energy was not measured. No seven-pair confirmation was triggered. Raw paired records are retained locally in `pair-1/` through `pair-3/`; the text-capture diagnostic is in the sibling `2026-10-26-e6-q2-staged-compute-256k-output-diagnostic/` directory.

# E6 Q2_0 staged-compute screen at 2K capacity

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 2048`, using the same staged profile, `pcie-frac=1`, and 512 prompt + 64 generated tokens. Model: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers. All resident maps matched (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`).

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | −1.32% | +3.41% | +0.88% | −0.28% | Match | 11.65 / 11.68 GiB |
| 2 | NInfer → Strata | +0.33% | +1.15% | −0.11% | −0.40% | Match | 11.71 / 11.71 GiB |
| 3 | Strata → NInfer | −0.65% | +3.49% | +0.54% | −0.68% | Match | 11.68 / 11.71 GiB |
| Median paired change |  | **−0.65%** | **+3.41%** | **+0.54%** | **−0.40%** | 3/3 match |  |

No median reached the 5% screen threshold, so no seven-pair confirmation was triggered. All outputs and resident maps matched; minimum available memory was 11.65 GiB, above the guard. This is a short-request 2K-capacity cell, not long-context evidence. Energy was not measured; clocks were observed read-only and changed dynamically. Raw records remain in `pair-1/` through `pair-3/`.

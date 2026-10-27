# E6 Q2_0 staged-compute screen at 32K capacity

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 32768`, for 512 prompt + 64 generated tokens. Both arms used `pcie-frac=1`, identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`), 3,000 expert slots, 6-GiB resident budget and 3-GiB workspace reserve. Model/profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | −1.28% | +1.14% | +1.36% | +0.59% | Match | 10.92 / 10.93 GiB |
| 2 | NInfer → Strata | 0.00% | −4.55% | +0.02% | +1.52% | Match | 10.94 / 10.94 GiB |
| 3 | Strata → NInfer | −2.60% | −3.41% | +2.62% | +3.13% | Match | 10.93 / 10.93 GiB |
| Median paired change |  | **−1.28%** | **−3.41%** | **+1.36%** | **+1.52%** | 3/3 match |  |

Measured outputs and resident maps matched throughout. Minimum available memory was 10.92 GiB, above the 6-GiB floor. No median reached the 5% screen threshold; no seven-pair confirmation was triggered. This is a short-request capacity screen, not long-context evidence. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

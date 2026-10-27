# E6 Q2_0 staged-compute screen at 4K capacity (2K prompt)

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 4096` for 2,048 prompt + 128 generated tokens. The shared staged residency map was `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`. Model/profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0, 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers, `pcie-frac=1` in both arms.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | −1.44% | +3.41% | +1.64% | +0.50% | Match | 11.63 / 11.64 GiB |
| 2 | NInfer → Strata | −1.44% | +2.30% | +1.43% | +0.51% | Match | 11.66 / 11.63 GiB |
| 3 | Strata → NInfer | +1.23% | −3.33% | −1.25% | −0.31% | Match | 11.65 / 11.67 GiB |
| Median paired change |  | **−1.44%** | **+2.30%** | **+1.43%** | **+0.50%** | 3/3 match |  |

Outputs and resident maps matched in all pairs. Minimum available memory was 11.63 GiB, above the 6-GiB floor. No median reached the 5% screen threshold, so no seven-pair confirmation was triggered. First-visible TTFT is client-observed to the first nonempty stream delta. Energy was not measured; clocks were observed read-only and varied. Raw paired records are in `pair-1/` through `pair-3/`.

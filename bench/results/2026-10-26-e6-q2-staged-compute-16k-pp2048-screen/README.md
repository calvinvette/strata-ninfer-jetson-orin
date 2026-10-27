# E6 Q2_0 staged-compute screen at 16K capacity (2K prompt)

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 16384`, for 2,048 prompt + 128 generated tokens. Both arms used `pcie-frac=1` and identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`). Profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | −2.58% | 0.00% | +2.56% | +1.83% | Match | 11.29 / 11.31 GiB |
| 2 | NInfer → Strata | −4.24% | −1.14% | +4.43% | +3.69% | Match | 11.32 / 11.32 GiB |
| 3 | Strata → NInfer | +8.10% | 0.00% | −7.43% | −5.54% | Match | 11.32 / 11.31 GiB |
| Median paired change |  | **−2.58%** | **0.00%** | **+2.56%** | **+1.83%** | 3/3 match |  |

All outputs and resident maps matched. Minimum available memory was 11.29 GiB. Pair 3 favored NInfer while the first two favored Strata on TTFT/client time, so effects are variable; no metric's median reached the 5% screen threshold and no seven-pair confirmation was triggered. This is a 2K prompt at 16K configured capacity, not long-context evidence. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

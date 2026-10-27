# E6 Q2_0 staged-compute screen at 4K capacity (172-token prompt)

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 4096`, for 172 prompt + 64 generated tokens. Both arms used `pcie-frac=1` and identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`). Profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | −1.35% | +23.33% | +1.18% | −6.58% | Match | 11.57 / 11.63 GiB |
| 2 | NInfer → Strata | −1.40% | 0.00% | +1.39% | +0.46% | Match | 11.63 / 11.62 GiB |
| 3 | Strata → NInfer | 0.00% | −0.89% | +0.55% | +0.57% | Match | 11.64 / 11.62 GiB |
| Median paired change |  | **−1.35%** | **0.00%** | **+1.18%** | **+0.46%** | 3/3 match |  |

Outputs and resident maps matched in all pairs. Minimum available memory was 11.57 GiB. The 23.33% decode-TPS increase and 6.58% shorter client time in pair 1 did not repeat; pair 2/3 changes were near zero. The median screen does not establish a performance gain, and no seven-pair confirmation was triggered. Energy was not measured; clocks were observed read-only and varied. This is a 172-token request at 4K capacity, not long-context evidence. Raw records are in `pair-1/` through `pair-3/`.

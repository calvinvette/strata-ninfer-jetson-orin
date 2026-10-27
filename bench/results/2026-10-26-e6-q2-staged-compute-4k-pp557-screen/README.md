# E6 Q2_0 staged-compute screen at 4K capacity (557-token prompt)

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 4096`, for 557 prompt + 64 generated tokens. Both arms used `pcie-frac=1` and identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`). Profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | −1.01% | +2.17% | +0.92% | +0.18% | Match | 11.58 / 11.63 GiB |
| 2 | NInfer → Strata | +1.99% | 0.00% | −1.93% | −1.37% | Match | 11.65 / 11.62 GiB |
| 3 | Strata → NInfer | −1.64% | −16.13% | +1.28% | +6.52% | Match | 11.60 / 11.63 GiB |
| Median paired change |  | **−1.01%** | **0.00%** | **+0.92%** | **+0.18%** | 3/3 match |  |

Outputs and residency matched in every pair. Minimum available memory was 11.58 GiB. No median reached the 5% screen threshold; no seven-pair confirmation was triggered. Pair 3 showed a decode TPS outlier (7.8 versus 9.3 tokens/s, rounded), which was not accompanied by an output mismatch. Treat the median as a screen, not a stable performance effect. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

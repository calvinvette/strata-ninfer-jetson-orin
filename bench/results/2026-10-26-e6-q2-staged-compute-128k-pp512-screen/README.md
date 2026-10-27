# E6 Q2_0 staged-compute screen at 128K capacity

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 131072`, for 512 prompt + 64 generated tokens. Both arms used `pcie-frac=1`, identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`), 3,000 expert slots, 6-GiB resident budget and 3-GiB workspace reserve. Model/profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | +0.45% | −2.41% | −0.59% | −0.08% | Match | 8.47 / 8.47 GiB |
| 2 | NInfer → Strata | −0.95% | 0.00% | +1.00% | +0.67% | Match | 8.47 / 8.49 GiB |
| 3 | Strata → NInfer | +3.79% | +5.00% | −3.51% | −3.94% | Match | 8.48 / 8.47 GiB |
| Median paired change |  | **+0.45%** | **0.00%** | **−0.59%** | **−0.08%** | 3/3 match |  |

All measured outputs and resident maps matched. Minimum available memory was 8.47 GiB, above the 6-GiB floor. No median reached the 5% screen threshold; no seven-pair confirmation was triggered. The 5.00% decode value in one pair is not a median effect. This is a short-request capacity test, not long-context performance. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

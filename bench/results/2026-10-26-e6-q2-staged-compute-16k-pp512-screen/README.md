# E6 Q2_0 staged-compute screen at 16K capacity

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 16384`, for 512 prompt + 64 generated tokens. Both arms used `pcie-frac=1`, identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`), 3,000 expert slots, a 6-GiB resident budget and 3-GiB workspace reserve. Model/profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | −4.81% | −5.62% | +4.76% | +4.87% | Match | 11.32 / 11.33 GiB |
| 2 | NInfer → Strata | +1.34% | 0.00% | −1.80% | −1.04% | Match | 11.36 / 11.34 GiB |
| 3 | Strata → NInfer | −2.92% | +3.49% | +1.83% | +1.09% | Match | 11.34 / 11.34 GiB |
| Median paired change |  | **−2.92%** | **0.00%** | **+1.83%** | **+1.09%** | 3/3 match |  |

All output and resident-map hashes matched. Minimum available memory was 11.32 GiB, above the 6-GiB floor. No median reached the 5% screen threshold; no seven-pair confirmation was triggered. This is a short-request capacity test, not long-context evidence. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

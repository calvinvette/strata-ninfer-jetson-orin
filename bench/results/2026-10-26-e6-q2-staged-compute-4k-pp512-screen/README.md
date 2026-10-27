# E6 Q2_0 staged-compute screen at 4K capacity

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 4096`, for a 512 prompt + 64 generated token request. Both used `pcie-frac=1`, identical 3,000-slot staged residency, 6-GiB resident budget, and 3-GiB workspace reserve. Model/profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0, MTP-2, prefill 128, 8 workers. Resident map SHA-256: `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | +2.69% | +4.88% | −2.46% | −3.28% | Match | 11.60 / 11.62 GiB |
| 2 | NInfer → Strata | −3.97% | −1.11% | +3.90% | +3.06% | Match | 11.63 / 11.67 GiB |
| 3 | Strata → NInfer | −1.97% | +2.27% | +2.18% | +0.95% | Match | 11.63 / 11.68 GiB |
| Median paired change |  | **−1.97%** | **+2.27%** | **+2.18%** | **+0.95%** | 3/3 match |  |

All measured output and resident-map hashes matched. Minimum available memory was 11.60 GiB, above the 6-GiB floor. No median reached the 5% screen threshold; no seven-pair confirmation was triggered. This is a short-request configured-capacity cell, not long-context evidence. Energy was not measured; clocks were sampled read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

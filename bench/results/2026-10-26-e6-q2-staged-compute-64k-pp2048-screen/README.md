# E6 Q2_0 staged-compute screen at 64K capacity (2K prompt)

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 65536`, for 2,048 prompt + 128 generated tokens. Both arms used `pcie-frac=1` and identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`). Profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | +1.55% | +2.44% | −1.33% | −1.60% | Match | 10.05 / 10.06 GiB |
| 2 | NInfer → Strata | −0.44% | −3.57% | +0.45% | +1.17% | Match | 10.08 / 10.07 GiB |
| 3 | Strata → NInfer | +0.89% | −1.20% | −1.01% | −0.48% | Match | 10.08 / 10.07 GiB |
| Median paired change |  | **+0.89%** | **−1.20%** | **−1.01%** | **−0.48%** | 3/3 match |  |

All output and resident-map hashes matched. Minimum available memory was 10.05 GiB, above the six-GiB floor. No median reached the 5% threshold, so no seven-pair confirmation was triggered. This is a 2K prompt at 64K configured capacity, not near-limit throughput evidence. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

# E6 Q2_0 staged-compute screen at 128K capacity (2K prompt)

Campaign window: 2026-10-26 to 2026-10-27 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 131072`, for 2,048 prompt + 128 generated tokens. Both arms used `pcie-frac=1` and identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`). Profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | +1.40% | 0.00% | −1.77% | −1.16% | Match | 8.41 / 8.42 GiB |
| 2 | NInfer → Strata | −0.46% | −3.75% | +0.43% | +1.49% | Match | 8.42 / 8.43 GiB |
| 3 | Strata → NInfer | −0.47% | +15.71% | +0.31% | −3.30% | Match | 8.36 / 8.37 GiB |
| Median paired change |  | **−0.46%** | **0.00%** | **+0.31%** | **−1.16%** | 3/3 match |  |

Outputs and resident maps matched across all pairs. Minimum available memory was 8.36 GiB. Pair 3 had a decode rate difference (7.0 versus 8.1 tokens/s, rounded), while other paired metrics were smaller. The median did not meet the 5% threshold; no seven-pair confirmation was triggered. This is a 2K prompt at 128K configured capacity, not near-limit performance. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

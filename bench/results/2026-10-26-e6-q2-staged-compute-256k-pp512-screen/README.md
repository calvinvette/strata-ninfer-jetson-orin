# E6 Q2_0 staged-compute screen at 256K capacity (512-token prompt)

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 262144`, for 512 prompt + 64 generated tokens. Both arms used `pcie-frac=1`, identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`), 3,000 expert slots, 6-GiB resident budget and 3-GiB workspace reserve. Model/profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | +16.57% | 0.00% | −14.36% | −11.22% | Match | 7.39 / 7.17 GiB |
| 2 | NInfer → Strata | −2.89% | 0.00% | +3.17% | +2.51% | Match | 7.10 / 7.13 GiB |
| 3 | Strata → NInfer | −13.78% | −2.78% | +16.18% | +12.59% | Match | 7.16 / 7.16 GiB |
| Median paired change |  | **−2.89%** | **0.00%** | **+3.17%** | **+2.51%** | 3/3 match |  |

All output and resident-map hashes matched. Minimum available memory was 7.10 GiB, above the six-GiB floor but with less margin than lower-capacity screens. Pair-to-pair variation was very wide (prompt TPS −13.78% to +16.57%; TTFT −14.36% to +16.18%), so the near-zero medians are inconclusive rather than evidence of equivalent speed. No median reached the 5% screen threshold; no seven-pair confirmation was triggered. This is a short-request capacity check, not long-prompt performance. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

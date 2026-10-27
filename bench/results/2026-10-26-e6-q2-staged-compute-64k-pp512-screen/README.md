# E6 Q2_0 staged-compute screen at 64K capacity

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute at configured `--max-context 65536`, for 512 prompt + 64 generated tokens. Both arms used `pcie-frac=1`, identical staged residency (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`), 3,000 expert slots, 6-GiB resident budget and 3-GiB workspace reserve. Model/profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0, MTP-2, prefill 128, 8 workers.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | −9.47% | +3.53% | +10.49% | +6.39% | Match | 10.09 / 10.11 GiB |
| 2 | NInfer → Strata | −0.37% | +1.15% | +0.45% | +0.06% | Match | 10.12 / 10.12 GiB |
| 3 | Strata → NInfer | +9.92% | −1.12% | −8.91% | −6.36% | Match | 10.12 / 10.14 GiB |
| Median paired change |  | **−0.37%** | **+1.15%** | **+0.45%** | **+0.06%** | 3/3 match |  |

Outputs and resident maps matched in every pair. Minimum available memory was 10.09 GiB, above the 6-GiB floor. The pair-to-pair spread was wide (prompt TPS −9.47% to +9.92%; TTFT −8.91% to +10.49%), while medians were near zero. No median met the 5% screen threshold and no seven-pair confirmation was triggered. Treat this as inconclusive screening evidence, not a speedup. This is a short-request capacity test, not long-context performance. Energy was not measured; clocks were observed read-only and varied. Raw records are in `pair-1/` through `pair-3/`.

# E6 Q2_0 staged-compute screen at 1K capacity

Date: 2026-10-26 (Orin AGX). Source: `87054b9c2d1426c6fa570eb42b660ea08d342136`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

Three randomized process pairs compared Strata grouped compute with strict NInfer grouped compute. Both arms used `pcie-frac=1`, configured `--max-context 1024`, and the same 3,000-slot/6-GiB staged expert residency map (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`). The model was Qwen3.8-Flash-Next GSQ-RCO Q2_0, MTP-2, prefill 128, 8 workers; request shape was 512 prompt + 64 generated tokens.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Output hash | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | +0.34% | +2.27% | −0.25% | −0.95% | Match | 11.67 / 11.72 GiB |
| 2 | NInfer → Strata | −2.35% | −10.47% | +2.52% | +5.33% | Match | 11.72 / 11.73 GiB |
| 3 | Strata → NInfer | −1.64% | −1.10% | +1.24% | +1.08% | Match | 11.72 / 11.76 GiB |
| Median paired change |  | **−1.64%** | **−1.10%** | **+1.24%** | **+1.08%** | 3/3 match |  |

The paired medians do not meet the 5% gain screen; no seven-pair confirmation was triggered. All six arms completed above the 6-GiB available-memory floor, and the measured output and residency hashes matched in every pair. First-visible TTFT is client-observed to the first nonempty stream delta. This is a short-request, low-capacity compute comparison, not evidence of long-context performance. Energy was not measured; clocks were sampled as read-only, dynamically changing observations. Raw records remain in `pair-1/` through `pair-3/`.

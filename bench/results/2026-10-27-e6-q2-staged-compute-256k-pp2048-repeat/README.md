# E6 256K 2,048+128 staged-compute repeat with text capture

Campaign window: 2026-10-26 to 2026-10-27 (Orin AGX). Source: `116070c390ad49c1aac58ade712ca4b65774a4ae`; binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

This randomized three-pair repeat compared Strata grouped compute and strict NInfer grouped compute at configured `--max-context 262144`, on the same Qwen3.8-Flash-Next GSQ-RCO Q2_0 staged profile and 2,048 prompt + 128 generated token request. Both arms used `pcie-frac=1` and the same residency map (SHA-256 `a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`). Temperature was 0; captured text is retained in each pair/arm directory.

| Pair | Order | Prompt TPS Δ | Decode TPS Δ | First-visible TTFT Δ | Client time Δ | Measured output hash (Strata / NInfer) | Minimum available RAM (Strata / NInfer) |
|---|---|---:|---:|---:|---:|---|---:|
| 1 | Strata → NInfer | +0.28% | −5.56% | −0.43% | +0.83% | `9bf815ae…` / `2ab94c82…` | 7.15 / 7.35 GiB |
| 2 | NInfer → Strata | +7.54% | +1.39% | −7.13% | −5.92% | `a868c120…` / `753ec32d…` | 7.37 / 7.39 GiB |
| 3 | Strata → NInfer | +5.57% | +8.57% | −5.27% | −5.66% | `753ec32d…` / `e63a8e95…` | 7.36 / 7.39 GiB |
| Median paired change |  | **+5.57%** | **+1.39%** | **−5.27%** | **−5.66%** | **0/3 match** |  |

All three measured output hashes differed between paired backends, so these timings do not qualify a performance gain. Although the median prompt TPS, TTFT and client-time changes cross the 5% screen threshold, the registered output-quality gate failed and no confirmation was triggered. Output variants also recur across different pair/arm positions (for example, pair-2 NInfer's measured hash equals pair-3 Strata's), indicating the divergence is not cleanly attributable to a particular backend from this sample. This run has no independent task-quality oracle; text difference is recorded as unresolved divergence, not as a semantic quality verdict.

Minimum available memory was 7.15 GiB, above the six-GiB floor. The decode/client timing direction varied across pairs; energy was not measured and clocks were observed read-only. This is a short request at large configured capacity, not a 256K prompt test. The prior one-pair text-capture diagnostic matched measured outputs, but this repeat's 0/3 paired match result supersedes it as the stronger repeatability evidence. Raw request records, text, residency and supervisor telemetry are retained in `pair-1/` through `pair-3/`.

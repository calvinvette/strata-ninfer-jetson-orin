# Phase 6 profile decision for Phase 7 qualification

## Selected test profile

Use this bounded Q2_0 profile for the next Phase 7 qualification runs:

| Setting | Value |
| --- | --- |
| Model | Qwen3.8-Flash-Next Coder GGUF, Q2_0, two-shard snapshot from the pinned ISTA-DASLab repository |
| Context | 8,192 tokens |
| KV | FP16 |
| Drafting | Off; no MTP model loaded (`--spec 2` verifier setting retained) |
| Expert cache | 3,000 exact slots |
| Prefill chunk | 128 tokens |
| CPU workers | 8 |
| Prompt cache | Disabled |
| Adaptive swaps | Disabled |
| Workspace reserve | 3,072 MiB |

This is a test profile for Phase 7, not a product default or general support
claim. Keep the existing captured graph behavior and other unlisted settings
unchanged. Models and packs stay under `~/models/strata-orin-validation/`.

## Evidence for this choice

The current-source [short retrieval-plus-arithmetic confirmation](../../bench/results/2026-10-17-phase6-q2-prefill-cache-current-source/README.md)
compared 3,000/3,500 exact expert slots with prefill chunks 32/128 in seven
randomized blocks. At 3,000 slots, chunk 128 reduced request time by 45.85%
(paired 95% interval −47.07% to −45.08%); all seven pairs favored chunk 128.
All 28 answers matched the exact 47-token oracle. The cache × chunk interaction
interval included zero, so the test uses the smaller 3,000-slot cache and makes
no claim that cache size improves performance at chunk 128. Minimum effective
admission availability was 13.49 GiB.

The held-out [7,501-token retrieval confirmation](../../bench/results/2026-10-17-phase6-q2-prefill-long-workload-current-source/README.md)
compared chunks 32 and 128 at exactly 3,000 slots. Chunk 128 reduced median
request time by 59.71% (paired 95% interval −59.82% to −59.52%); all seven
pairs favored it, and all 14 answers matched the exact 36-token oracle.
Minimum host/effective admission availability was 18.07/11.39 GiB. Its
`VIN_SYS_5V0` request-window integral per output token fell 59.54% (paired
95% interval −59.59% to −59.44%). This rail includes board idle and background
activity and is not process-attributed.

In the same-day short test, the `VIN_SYS_5V0` request-window estimate fell
44.23% with chunk 128 (six supported pairs, paired 95% interval −45.23% to
−39.54%). One rail window was unsupported because of a telemetry gap. These
separate rail observations support the latency choice but do not complete the
process-energy Pareto analysis.

The current-source [Q2_0 graph × MTP confirmation](../../bench/results/2026-10-17-phase6-q2-graph-mtp-current-source/README.md)
found no reliable captured-versus-eager request-time change on its
2,094-token processor task. MTP2 increased request time by 5.46% with capture
and 3.39% in eager mode, while both routes returned the same rubric-passing
answer. This supports leaving drafting off for this tested task and preserving
the existing graph setting; it does not establish a universal MTP result.

## Limits and next gate

The decision covers one Q2_0 artifact, 8K context and the listed short and
long retrieval workloads. It does not choose a profile for IQ1_M, other
quantizations, larger context, concurrency or other hardware. IQ1_M remains
unselected because its MTP × KV effect changes with prompt length and its
adaptive routing has a persistent-state divergence under tested swaps.

The selected profile has passed a supervised 30-minute, 512-token
retrieval-plus-arithmetic streaming soak with exact answers and the six-GiB
physical-headroom guard; see the [sustained-service report](../../bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/README.md).
It also passed one 7,498-token 8K near-limit retrieval and same-service
recovery check; see the [recall report](../../bench/results/2026-10-17-phase7-q2-prefill128/near-limit-8k-recovery/README.md).
These results now also include passing selected-profile decode cancellation,
progress-confirmed active-prefill cancellation, same-service recovery, and
three-cycle fresh-service teardown with listener and process-exit checks. See
the [teardown report](../../bench/results/2026-10-17-phase7-q2-prefill128/teardown-3cycle/README.md).
They do not cover other task types or other context sizes on the selected
profile. Do not promote a default until those checks, process-relevant energy
evidence and the broader Phase 6 interaction gates are complete. Phase 6 and
Phase 7 remain open.

## MTP4 screening result

A randomized three-block [MTP-off/MTP4 × FP16/INT8 KV × short/near-limit
screen](../../bench/results/2026-10-24-phase6-coder-mtp4-kv-heldout-length-screen3/README.md)
passed all 24 answer checks. On the 512-token task MTP4 improved decode
throughput by 10.29% with FP16 KV and 11.35% with INT8 KV, while client total
time was statistically unresolved. On the 7,501-token task MTP4 reduced decode
throughput by 10.95% and 8.80%, respectively; total-time intervals included
zero as prefill dominated. This length-dependent tradeoff supports leaving MTP
off in the selected Q2_0 serving profile. It does not qualify MTP4 on held-out
prompts or persistent state, and it contributes no energy-per-token measurement.
Phase 6 remains open.

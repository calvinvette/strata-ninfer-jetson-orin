# Phase 5 closeout — bounded Orin single-live transaction and graph scope

Phase 5 is complete for the tested Orin single-live, static-routing contract.
The release profile remains Q2_0 with MTP off; MTP windows and graph behaviors
below are separately tested options, not product defaults. Multi-live batch
decode and adaptive CPU/GPU expert migration remain excluded because their
persistent-state and output-parity gates do not pass.

| Gate | Evidence and result |
| --- | --- |
| Accepted-prefix transaction | Current Coder IQ1_M MTP off/2/3/4 checks matched token IDs and all nine persistent fields at every shared commit on 512- and 2,048-token inputs; current-source long-prompt FP16 checks cover 7,498 tokens. The MTP4 chain extension matched every shared state boundary and final state for 256 generated tokens and a natural-EOS 348-token chain. See the [MTP4 long-chain report](../../bench/results/2026-10-24-phase5-coder-mtp4-accepted-prefix-long-chain/README.md) and [long FP16 matrix](../../bench/results/2026-10-20-phase5-coder-current-source-mtp-prefix-long-fp16/README.md). |
| Rejection and recovery | Current-source MTP3 rejection/recovery passed on short and 7,501-token prompts, with output and shared main-model state fingerprints matching MTP off through recovery. MTP4 long-chain accepted prefixes are exact in the tested uninterrupted cases. See [short recovery](../../bench/results/2026-10-23-phase5-coder-mtp3-rejection-recovery/README.md) and [near-limit recovery](../../bench/results/2026-10-23-phase5-coder-mtp3-long-rejection-recovery/README.md). |
| Cancellation and service recovery | The Coder IQ1_M MTP2 cancellation check matched all five recorded accepted-prefix token/state boundaries and recovered on the same service. This is a bounded cancellation set, not every token boundary. See the [cancellation report](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md). |
| Graph transaction lifecycle | The current Coder graph pool passed forced-cap eviction/recapture and default-cap stress: the default-cap 80-request run exercised 88 layouts and 26 evictions with all requests completing. These are lifetime checks, not a speed claim. See the [graph lifecycle report](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md). |
| Functional regression | The current Orin CUDA suite registered 135 cases: 132 passed, two optional IQ fixture cases skipped, and `pool_test` lacked its default `pack/full/experts.bin`. Re-running `pool_test` with the existing external Q2_0 fixture passed. The verifier convolution parity test passed T=1..8 and every split offset. See the [CTest report](../../bench/results/2026-10-24-orin-cuda-functional-ctest/README.md). |

## Unsupported behavior and limits

- Multi-live target-only and batch-MTP decode can emit different tokens and
  persistent state from isolated serial controls. Prompt/slot reversals and
  owner-path interventions localize contributors but have not established a
  general repair. Do not treat output parity at short lengths as state parity.
- Adaptive CPU/GPU migration can change accepted-prefix state on long chains.
  The release profile disables adaptive swaps. No replay or precision change is
  promoted.
- MTP performance depends on prompt length, KV format and workload. MTP remains
  off in the selected Q2_0 release profile; Phase 6 records its measured cells.
- Graph-pool lifecycle tests establish eviction/recapture behavior only. They
  do not qualify concurrent batch correctness or a graph speedup.

Reopen Phase 5 before enabling multi-live decode, adaptive migration, or a new
MTP/model/KV domain. This closeout does not claim those paths are correct.

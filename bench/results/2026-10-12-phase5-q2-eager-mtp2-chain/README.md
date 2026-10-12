# Captured and eager Q2_0 MTP2 32-token state check — 2026-10-12

This check extends eager/captured correctness from eight output tokens to a
32-token chain. It ran the existing accepted-prefix harness in separate
28-GiB-supervised processes for captured and `--no-capture` eager routes. Each
route compared MTP window 2 to its own no-MTP reference, then
`cross-route-comparison.json` compared the MTP2 traces directly.

Both harness runs passed. They used the same formatted 512-token prompt
(`ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`), Q2_0
pack, 3,000 expert-cache slots, FP16 KV, 8K configured context and disabled
CPU-prefill sharing. Each route offered 18 drafts and accepted 13. Captured and
eager modes emitted identical 32 token IDs, matched all nine persistent state
fields at all 19 commit boundaries and matched final state.

Minimum host availability was 17.14 GiB captured and 17.18 GiB eager. Minimum
effective admission headroom was 15.65 and 14.80 GiB, respectively. The
ordinary six-GiB floor was maintained under the 28-GiB cgroup cap. Clock
observations were read-only and dynamic; EMC reads were denied by the board.
Energy was not measured. This is one prompt and one process per route, so it is
correctness evidence only, not a performance, quality or broad long-chain
qualification.

The parent harnesses retain per-arm engine logs, accepted-prefix traces, exact
state hashes, output IDs and supervisor telemetry. `cross-route-comparison.json`
records the cross-route result. The binary SHA256 was
`1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`.

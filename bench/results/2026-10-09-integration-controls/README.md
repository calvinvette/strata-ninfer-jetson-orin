# Integration control checkpoint, 2026-10-09

Fresh measurements on Orin, not inherited integrated-runtime results. Phase 1 is
in progress. No NInfer runtime component or optimization has been introduced.
Runtime sources match Strata `0be090c`; the branch checkpoint is `0c08fa5` plus
the new Python harness and documentation. Models remain under `~/models/`.

Both isolated native ARM64 Release builds completed using two jobs each, GCC
11.4 and CUDA 12.6.68. Binary inventories preserve digests and SM87 cubin lists.
The branch build was supervised with six GiB physical/cgroup headroom. Its
memory summary is build evidence, not inference performance. Full build logs
remain under ignored `build/integration/`; compact configure/identity evidence
is retained here. CUDA probe, power-mode query and raw tegrastats are fresh.
MAXN is reported; clocks were not changed or locked. `jetson_clocks --show`
requires root and failed explicitly; raw tegrastats retains observed clocks.

| Check | Fresh result | Scope |
| --- | --- | --- |
| Integration tests | 19 pass | Lifecycle/pressure/cleanup, workload qualification and offline planner |
| Jetson setup tests | 15 pass | No model or GPU execution |
| Selected API regressions | 312 pass | Mock engine: server, security, lifecycle, cancellation, request accounting |
| Pinned core test | 1 pass | Physical memory budget arithmetic |
| Branch core tests | 6 pass | Memory budget, message boundaries, conversation cache, coupled draft, probabilistic acceptance and bf16 bits |
| Model shard verification | 2 pass | Independent SHA256 against pinned IQ1_M digests |
| MTP source verification | 31 pass | Independent SHA256 against pinned tensor digests |
| Prepared runtime packs | Identity hashes | No new conversion/codec qualification |
| Formatted inputs | Exact 512/2048/172/557/1069 | Tokenizer/template identities retained |
| Native model smoke | Both complete | Input 248045 → output 846; no MTP weights, native spec4 |

No skips are reported in the selected Python/core suites. Unbuilt/unselected
upstream tests are excluded, not counted as passing. The omitted upstream
`tests/` tree prevents treating this as a full engine suite.

The pinned smoke sampled at least 9,397,497,856 available physical bytes (8.75
GiB); the branch smoke sampled at least 10,109,693,952 bytes (9.42 GiB). Both
preserved the six GiB floor. Automatic expert allocations differed: 5,419 slots
versus 7,066. These are one-token startup/execution checks with unmatched cache
state; their printed rates are **not a throughput comparison** or numerical
parity evidence. Swap was present; raw samples retain its scope and values.
The token matches the inherited one-position observation, but no new independent
logit oracle run or multi-token parity pass is claimed.

Two failed attempts remain in `failed-subcommand/` and `unsupported-spec0/`.
The executable takes flags directly despite the help text's `strata generate`
label. Native IQ packs reject `--spec 0`. The successful checks retain `--spec 4`
and omit `--mtp`; future MTP-off factor translation must preserve native-window
requirements and check actual drafted/accepted counters before benchmarking.

[Capabilities](capabilities.json) explicitly records the unrun paired API
campaign, first-token telemetry, owner allocation/graph/workspace counters,
independent tolerances, NInfer cohorts and HIP/SYCL checks. HIP/SYCL were not
rebuilt because this checkpoint changes only Python harnesses and documentation,
not shared engine/backend source. The known raw multi-token logit discrepancy
remains open. Three-request screening, seven independent paired confirmation
blocks and later integration phases have not been completed.

Reproduction: [Phase 1 harness](../../../docs/integration/PHASE1.md).
Transfer notes: [future Strata + Splash work](../../../docs/integration/PORTING_NOTES.md).

Later same-day measurements are in the [paired control continuation](../2026-10-09-paired-api-controls/README.md). This checkpoint preserves its original measurement scope.

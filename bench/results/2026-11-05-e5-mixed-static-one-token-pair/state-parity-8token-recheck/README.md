# Coder mixed-backend service state mismatch

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is an E5
correctness diagnostic, not a performance or answer-quality result.

## Setup

The two private `StrataEngine` service arms used the same current binary
(`574de07d`, SHA-256 `42fbb0afd69eb11979884352584a5f14f141b3e3ed5a6e87eef4a780aa721b2c`),
Coder IQ1_M two-shard GGUF at
`~/models/strata-orin-validation/Coder-GGUF/IQ1_M/` (shard SHA-256 values
`e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` and
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`), pack
identity (`index.txt` SHA-256
`2cb3352786bcae81ea4d933eee6b2d5db45774069320c924a6dea48eb65a3cd3`),
the same expert profile (SHA-256
`c1e66c2e60ae8e7880befa303fb6bb79da1ccdd59895053eb95d433c648ef047`),
`--expert-cache 256`, four pool workers, prefill 64, 512 context, prompt IDs
`1,2,3`, greedy sampling and eight generated tokens. Startup reported 391
cached experts (0.63 GiB) in each arm. Both set
`STRATA_PREFILL_CPU_SHARE=0`; the only requested backend change was
`--expert-backend strata` versus strict `--expert-backend ninfer`.

The prompt IDs were sent through the service `GEN` path. State fingerprints and
accepted-prefix traces were enabled. Both completed normally and NInfer logged
all seven mixed-codec route dispatches.

## Result

| Backend | Generated token IDs | Accepted-prefix entries | Final state |
| --- | --- | ---: | --- |
| Strata | `4,5,6,24218,10,4838,1665,15` | 8 | reference |
| Strict NInfer | `5,6,24218,10,4838,1665,15,16` | 8 | differs in `gdn`, `ple`, `tail`, `dead`, `pooled`, `pooled_full`, `kv`, `ple_prev` |

The output first differs at generated token 1. Persistent-state hashes differ
at every common accepted-prefix boundary, beginning with the first committed
token. The offline comparator reports `passed: false`. This does not identify
the cause of the generated-token change, but an all-layer verifier-input
capture narrows the first activation difference to after model layer 0. At all
three prompt positions, layer-0 inputs are bit-identical, and layer-0 route IDs
and weights match. Captured layer-0 expert parts differ at relative L2
`5.83e-8`–`7.14e-8`; combined output is exact at position 0 and differs by
`3.26e-8`–`4.59e-8` at positions 1–2. Layer-1 inputs first differ, at relative
L2 `7.11e-8`–`8.40e-8` (1,155–1,531 of 2,560 values; maximum absolute delta
`2.98e-7`). These are small numerical deltas; no independent oracle has yet
checked these exact service activations, and causality for the token change is
not established. The integration has not passed exact same-prompt token/state
parity, though task-quality impact remains unmeasured.

A separate one-token service pair also returned `4` for Strata and `5` for
strict NInfer, with different final fingerprints. Both strict runs logged seven
tuple dispatches. These differ from the earlier direct one-shot CLI smoke, in
which the two backends returned token `5`; that CLI smoke is not evidence of
service parity and must not be used to claim it.

## Evidence and limits

Raw engine logs and the machine-readable comparison are in this directory;
one-token logs are in the sibling `state-parity-1token/` directory. The exact
model paths, geometry and file sizes are included in the logs; the prior model
identity manifest is [here](../../2026-10-21-phase6-coder-current-source-cache-context-screen3/model-sha256.txt).
The [all-layer input comparison](../state-moe-inputs/comparison.json) and
[layer-0 route/output comparison](../state-moe-layer0/comparison.json) include
the diagnostic summaries and their raw captures.
State instrumentation changes execution cost, so no timing comparison is
reported. These short synthetic token-ID requests do not measure answer quality,
held-out tasks, long-context behavior, or memory minima.

Next E5 action: reproduce with a natural held-out prompt and layer/operator
captures, then identify and fix the first numerical/state divergence before
expanding MTP or adaptive-policy tests. The reusable comparator is
[`compare_ninfer_backend_state.py`](../../../../tools/integration/compare_ninfer_backend_state.py).

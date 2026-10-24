# MTP3 seven-block same-prompt replication — Orin — 2026-10-23

Seven randomized paired blocks compared MTP off and MTP3 using fresh processes,
with one shared distinct warmup and one measured request per process. All 14
cells and API requests passed. Paired response content matched in all seven
blocks, as did the harness's non-MTP arguments, KV format and expert residency.
Prompt caching was disabled.

The median paired decode-throughput delta was +4.34%, with a paired-block
bootstrap 95% interval of +3.86% to +5.57%. The seven deltas were +3.32%,
+4.34%, +21.70%, +4.73%, +5.57%, +3.98% and +3.86%; the high third-block
effect is retained. MTP3 drafted 34 tokens and accepted 28 in every measured
request. Median TTFT delta was -2.20%, and median total-request-time delta was
-2.58%; the individual TTFT and total-time deltas are in `paired-summary.csv`.
The observed minimum physical-memory availability was 16.79 GiB, above the
6 GiB admission floor; sampled cgroup memory-event counters remained zero.
Tegrastats clocks, temperatures and named rails are retained per cell. Energy
was not integrated, and the run does not establish thermal steady state.

## Scope and limits

This is seven independent request-pair repetitions for **one prompt**. It
replicates the earlier screen and narrows timing uncertainty for that prompt,
but it is not held-out prompt confirmation as required by Phase 6. This
no-trace timing harness checked output content but did not record accepted-prefix
persistent-state fingerprints; separate state and recovery probes provide only
their individually documented scopes. The result does not qualify MTP3 across
long prompts, KV profiles, graph settings or broader quality tasks, and does
not promote a default.

## Identity

- Source HEAD: `20a8c130` (current repository code at launch).
- Device: Orin AGX, native aarch64, CUDA runtime path, shared physical RAM.
- Model: Coder IQ1_M GGUF shards with the same upstream base-checkpoint MTP
  weights used in the preceding held-out MTP screen; immutable model artifacts
  remain under `~/models/strata-orin-validation`.
- Workload: `coder-mtp4-heldout-retrieval-arithmetic-512`, 512 prompt tokens,
  45 completion tokens before natural stop. It is the same prompt used in the
  preceding three-block screen; the workload file and exact per-cell configs
  are retained here.
- Seed: 20261024; arms were randomized within each block.
- `campaign.json`, requests, engine logs, resource samples, tegrastats and
  `SHA256SUMS.txt` preserve the command and raw evidence.

## Next step

Use at least one genuinely different held-out prompt for MTP-off/MTP3
confirmation, then evaluate the relevant KV and graph interactions. Keep Phase
5 open for adaptive state and multi-live correctness evidence, and Phase 6 open
until held-out confirmation and broader Pareto/energy analysis are complete.

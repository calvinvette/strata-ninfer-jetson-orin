# Current-source MTP window screening — Orin — 2026-10-23

Three randomized paired blocks compared MTP off, window 2, 3 and 4 on the
same held-out Coder IQ1_M workload. Each cell ran in a fresh process with a
shared distinct warmup request, then one measured 512-token prompt and up to
48 generated tokens. Prompt cache was disabled. Every process and measured API
request passed; paired API response content matched. The harness also checked
matching non-MTP arguments, runtime KV format and expert residency.

This is a screening result (n=3 per window), not a confirmation or a promoted
default. All three MTP windows drafted more than zero tokens and accepted
21/24, 28/34 and 33/42 for windows 2, 3 and 4 respectively, in every block.
MTP3's decode throughput delta median was +5.24% (bootstrap interval
+3.75% to +6.14%); its three paired deltas were +3.75%, +6.14%, +5.24%.
MTP4's median was -0.11% (interval -0.82% to +1.78%), with small opposing
per-block deltas. MTP2's median was +1.57%, but one candidate measured 5.11
Tok/s against 12.15 Tok/s off (-57.96%); the other two deltas were +2.61% and
+1.57%, producing a very wide bootstrap interval (-57.96% to +2.61%). Retain
that outlier; no timing conclusion or preference for MTP2 follows from this
small screen. MTP3 TTFT deltas were -0.04%, -3.83%, and -2.09%; per-request
total time also improved slightly in these blocks. The observed minimum
physical-memory availability across all runs was 16.81 GiB, above the
6 GiB admission floor, with zero sampled cgroup memory events. Named tegrastats
rails and clock/temperature samples are retained per cell; energy is not
integrated here and the measurement is too small to characterize thermal
steady-state behavior.

## Identity

- Source: repository HEAD `eae81cf7cd8abce63299fa9ec4b560c3fc27ba44`.
- Device: Orin AGX, native aarch64, CUDA runtime path, shared physical RAM.
- Model: Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M Coder GGUF; two shards. SHA256:
  - `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` — shard 1.
  - `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` — shard 2.
- MTP weights: upstream base-checkpoint MTP files in
  `~/models/strata-orin-validation/mtp/rt` (same set used by the preceding
  held-out MTP × KV screen).
- Workload: `coder-mtp4-heldout-retrieval-arithmetic-512`, three retrieval
  markers plus checksum arithmetic, 512 prompt tokens, 45 completion tokens
  before natural stop; detailed prompt and expected answer are in
  `selected-workloads.json`.
- Seed: 20261023. Order randomized within each block.
- Exact command and per-cell configs, requests, full engine/supervisor output,
  memory samples and tegrastats are preserved in this directory.

## Interpretation and next step

MTP3 is the leading screening candidate on this single short retrieval workload,
with no observed TTFT penalty and matching API content. This does not establish
accepted-prefix persistent-state parity for all MTP3 cells, general quality,
long-workload benefit, or an interaction with KV, graph, cache, or prefill
chunk. Pair MTP3 and MTP-off across held-out prompts in the planned seven-block
confirmation, and retain windows 2/4 only if their question is explicitly
under study. Continue Phase 5 state/rejection/recovery checks independently;
Phase 5 and the broader Phase 6 Pareto/interaction gates remain open.

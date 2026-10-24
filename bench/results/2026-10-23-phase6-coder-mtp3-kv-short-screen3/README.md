# MTP3 × KV short-workload screen — Orin — 2026-10-23

Three randomized blocks screened MTP off/MTP3 × FP16/INT8 KV on the distinct
512-token Coder IQ1_M held-out retrieval/arithmetic workload. Each of the 12
cells used a fresh engine in a 28 GiB systemd memory scope, one shared distinct
warmup, one measured request and prompt caching disabled. All cells passed;
all answers matched the independent expected marker/sum oracle. Runtime KV and
actual expert residency matched the requested cells (1,934 slots, 3,807 MiB).
The six-GiB physical availability floor was maintained; minimum observed
availability was 17.00 GiB and sampled cgroup memory events were zero.

MTP3 decode throughput improved by a median 7.78% under FP16 KV (paired
bootstrap 95% interval +7.28% to +7.99%) and 7.89% under INT8 KV (interval
+7.54% to +8.19%). The MTP × KV ratio-of-ratios for decode throughput was
+0.38% (interval -0.41% to +0.57%), so this screen detected no KV interaction
for the tested task. The MTP3 median total-time change was -0.39% under FP16
and +0.69% under INT8, with both intervals spanning zero. The screen's
three-block estimates do not establish equivalence or a default.

GPU clocks were observed dynamically from 306 to 1,300.5 MHz over measured
request windows; EMC clock readback was denied. The raw tegrastats also retain
CPU clocks, temperatures and named rails. Rail energy was not integrated, and
this was not a sustained thermal run.

## Reproduction and identity

- Runner source commit: `465056c6db218f096c54833d1fed9eca0244cc0a`.
- Candidate binary SHA256: `1f44e7e3713faf9d1e1fee688a69ce5960e21d40c1d0d6071e9831dea53316d6`.
- Device: Orin AGX, native aarch64, shared physical RAM.
- Model: Coder IQ1_M two-shard GGUF with base-checkpoint MTP weights; all
  artifacts remain in `~/models/strata-orin-validation`.
- Workload: `coder-mtp-retrieval-short-512`, a distinct prompt with three
  marker codes and sum 1478; exact input and expected answer are retained in
  `selected-workloads.json`.
- Seed: 20261027; all four cells were randomized within each block.
- `campaign.json`, `config-source.json`, every cell's config/request/engine
  output, supervisor samples, clock windows and tegrastats are retained.
  `SHA256SUMS.txt` covers the complete report directory.

This is one short workload and three repetitions. It combines the held-out
short-task MTP effect with KV format but does not cover near-limit MTP3 × KV,
accepted-state interactions with quantized KV, graph × speculation, energy
Pareto or a broad quality suite. Phase 5 and Phase 6 remain open; no default
changed.

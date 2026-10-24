# Held-out MTP3 retrieval confirmation — Orin — 2026-10-23

Seven randomized paired blocks compared MTP off and MTP3 on a distinct
512-token Coder IQ1_M retrieval/arithmetic prompt with three new marker codes.
Each cell ran in a fresh process, after a shared distinct warmup, with prompt
caching disabled. All 14 cells and measured API requests passed. Paired output
content matched in every block, and an independent check against the workload
oracle confirms all 14 answers exactly returned the three marker codes and sum
1478. The screen also verified matching non-MTP arguments, actual KV format and
expert residency.

MTP3 drafted 34 tokens and accepted 31 in every measured request. Median paired
decode-throughput delta was **+10.25%**, with a paired-block bootstrap 95%
interval of +8.98% to +10.49%; the seven deltas were +6.99%, +10.91%, +10.27%,
+10.25%, +8.98%, +8.99%, and +10.49%. This is a consistent decode gain on this
prompt and MTP setting.

Two MTP3 arms had severe prefill/TTFT outliers: blocks 0 and 4 took 56.63 s and
57.89 s to prefill 512 tokens, versus 26.15 s and 27.33 s in their MTP-off
controls. Their TTFT deltas were +116.97% and +99.61%, and total-request deltas
+101.23% and +87.13%. The other five TTFT deltas ranged -2.32% to +0.75% and
total-request deltas ranged -3.21% to -0.54%. These are retained in the paired
analysis. The recorded clocks vary by cell; the logs do not identify a single
cause, so this screen supports a decode-throughput result but not a stable
end-to-end latency claim. The median TTFT delta was -0.41% and median total
request delta -1.42%, but those medians conceal the two large candidate outliers.

Minimum observed physical/admission availability was 16.85 GiB, above the
6 GiB floor; sampled cgroup memory events were zero. Tegrastats includes CPU
clock samples, temperatures and named power rails. GPU clock frequency
readback was unavailable and rail energy was not integrated. This is not a
thermal steady-state test.

## Identity and limits

- Source HEAD at run launch: `b35a6d04`.
- Device: Orin AGX, native aarch64, CUDA runtime path, shared physical RAM.
- Model: Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M Coder GGUF plus upstream base-checkpoint
  MTP weights; artifacts remain under `~/models/strata-orin-validation`.
- Workload: `coder-mtp-retrieval-short-512`, 512 prompt tokens, 47 completion
  tokens through natural stop; expected answer and independently checked cell
  outputs are in `semantic-check.json`.
- Seed: 20261026; arms randomized within each block.
- Full command, configurations, request records, logs, memory and tegrastats
  samples are retained here; hashes are in `SHA256SUMS.txt`.

This confirms the expected synthetic retrieval task and decode performance for
one held-out prompt. The no-trace screen does not inspect accepted-prefix
persistent state or establish general quality. Phase 5 remains open for
adaptive state and multi-live behavior. Phase 6 remains open for additional
held-out workload families, graph/KV interactions, response modeling and energy
Pareto analysis. No default was changed.

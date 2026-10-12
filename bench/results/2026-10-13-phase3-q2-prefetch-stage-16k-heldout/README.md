# Q2_0 16K prefetch fill versus staging confirmation — Orin — 2026-10-13

This seven-pair held-out confirmation compared async prefetch that fills the
page cache (`staging=0`) with the same prefetch path plus host staging
(`staging=1`). It used the Qwen3.8-Flash-Next Q2_0 model and PLE artifacts
already retained under `~/models/strata-orin-validation/`. Artifact revision,
GGUF shard hashes, and candidate binary identity are recorded in the preceding
[16K transfer report](../2026-10-13-phase3-q2-mapped-pread-16k-heldout/README.md).
The exact 16,384-token `heldout_blue` prompt, IDs and tokenizer identity are in
[`prompt.json`](prompt.json); the 3,000-slot base configuration is
[`base-config.json`](base-config.json).

All seven pairs passed: generated IDs, effective cache slots and all nine
persistent state fingerprints matched within each pair. With eight generated
tokens, prefetch-fill had a 100.676 s median request time; prefetch-stage had
101.572 s. Staging's paired median request delta was +0.40% (95% paired
bootstrap interval +0.17% to +1.86%), so staging was measurably slower in this
configuration, though well below the 5% promotion threshold. Median prompt
time was +0.40% slower with staging (95% interval +0.06% to +1.91%); decode
time was −0.67% (−3.38% to +0.60%). Do not promote staging from this result.

Median process major faults were 38,262 for fill-only and 58,975 for staging;
minor faults were 361,849 and 357,698. Physical NVMe reads are whole-device
measurements and include unrelated host activity and kernel readahead. The
shared page cache was not flushed, so this is a warm/shared-cache comparison,
not a cold-storage result. Whole-board tegrastats rail estimates include
unrelated activity and are neither process-attributed nor additive; they do
not establish per-request energy.

The run used a 28-GiB systemd memory cap and the independent supervisor's
six-GiB admission floor. Minimum host availability was 17.77 GiB, minimum
effective scope headroom was 7.32 GiB, and OOM-kill counters remained zero.
CPU and GPU clocks varied dynamically; EMC clock readback was unavailable and
no clocks were changed. The supervisor recorded 1,614 memory samples over
1,704.6 seconds and returned exit code 0. The complete result and raw board
samples are in `experiment-7pairs/`; supervisor evidence is in `supervisor/`.
Per-arm engine logs are ignored by Git and their SHA256 identities are listed in
[`ENGINE_LOG_SHA256.txt`](ENGINE_LOG_SHA256.txt).

[`analyze.py`](analyze.py) recomputes timing intervals, parity, memory floor,
major/minor faults and board-rail summaries from the retained files;
[`analysis.json`](analysis.json) contains its output. This rejects staging for
this prompt and cache configuration, not every possible staging workload.
Phase 3 remains open for broader pressure, unique physical backing and graph
accounting gates.

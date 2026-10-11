# Prefill chunk 32 vs 128 paired screen — Orin — 2026-10-11

Seven same-day independent process pairs compared `--prefill 32` with
`--prefill 128` on the current CUDA candidate. Both arms used the same Qwen3.8
Flash-Next Coder IQ1_M model and MTP files, profile, 4,096 context, 5,000
max-blob-equivalent expert-cache budget, 3,072 MiB workspace reserve, one pool
worker, `--prompt-cache 0`, and the same formatted 512-token prompt. All runs
completed eight output tokens and passed the six-GiB `MemAvailable` supervisor.
The sized cache reported 6,519 actual variable-size slots in every arm. The
candidate and baseline output text hashes matched within all seven pairs.

| Client metric | Chunk 32 median | Chunk 128 median | Paired candidate/control median ratio | 95% paired bootstrap interval |
| --- | ---: | ---: | ---: | ---: |
| Total request time | 19.889 s | 7.363 s | 0.370 (−63.0%) | 0.360–0.390 |
| First visible delta (client TTFT) | 19.278 s | 6.739 s | 0.349 (−65.1%) | 0.340–0.367 |
| Prompt rate | 26.7 tok/s | 77.3 tok/s | 2.895 (+189.5%) | 2.749–2.978 |
| Decode rate | 11.7 tok/s | 11.0 tok/s | 0.932 (−6.8%) | 0.889–0.982 |

The interval resamples seven whole paired process blocks (50,000 bootstrap
replicates, seed 870126). The exact per-block request and stage samples are in
`campaign/paired-analysis.json`; all raw API responses, engine logs, commands,
tegrastats and physical-memory samples remain in `campaign/` and `extension/`.
The realized order was baseline-first in four pairs and candidate-first in
three. Minimum `MemAvailable` was 8.44 GiB overall (8.59 GiB baseline median,
8.52 GiB candidate median), above the ordinary six-GiB floor.

This screen shows a substantial prefill/TTFT improvement and a modest decode
rate reduction for this short prompt and eight-token completion. It does not
qualify a default change: it uses one prompt only, not held-out confirmation;
output equality covers only the eight returned tokens; power/energy, disk I/O,
page faults, actual transient prefill allocation size, and GPU/EMC clocks were
not measured. CPU clocks varied from 729 to 2,201 MHz, and temperatures from
50.3 to 57.7 C. The code-reported profile is unchanged and the engine source
and binary hashes are recorded in `campaign/paired-analysis.json`. No model,
pack or runtime artifact was added to Git; all remain under `~/models/`.

Both JSON configs differ only in prefill chunk size. The workload file retains
the exact API prompt and tokenizer identity. The first three pairs were run as
one three-block screen; four more blocks used `run_paired_controls.py`'s
completed-campaign extension with a seed chosen to counterbalance process
order. This is one Phase 3 resource/performance cell, not Phase 6 multivariate
confirmation; Phase 3 remains open for other transfer/admission gates and graph
executable/driver memory attribution.

# Q2_0 expert-cache × context accepted-state screen — Orin — 2026-10-12

This randomized 2×2 screen separates configured context reservation from
expert-cache capacity in the repeatable state difference previously seen
between 3,000- and 5,000-slot cache settings. It used the current candidate
(`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`), the
Q2_0 model and PLE pack under `~/models`, the same fixed 512-token formatted
prompt, and a 511-token committed prefix followed by one generated token.
Each setting ran in three fresh processes, with the four cells randomized
inside each repetition (seed `202610126`). Prefill 512, spec 2, CPU prefill
sharing disabled, mmap expert reads, prompt cache 6 and the separate 3,072 MiB
workspace reserve were held fixed. Each run dumped full float32 GDN state at
the accepted-prefix boundary `L=511` and logged the other accepted-state
fingerprints.

All 12 cells passed. They selected token 271, used the same prompt hash
(`bbbcc4221a991dc78f6de446e4ed7faafed0e984026ab969f4de6747a02f2004`) and
repeated exactly within each cache/context cell. The minimum whole-board host
availability was 14,668,005,376 bytes (13.66 GiB); the six-GiB guard was
preserved. Every owner log had 304 allocation and 303 free events, and only
the expected 1,485,606,400-byte weight arena remained live at log end.

| `--expert-cache` | Configured context | Expert-cache owner peak | Session owner peak | Hits / lookups | Minimum host availability |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 8,192 | 4,147,200,000 B | 343,102,976 B | 68 / 480 | 17.69 GiB |
| 3,000 | 65,536 | 4,147,200,000 B | 1,856,067,072 B | 68 / 480 | 16.28 GiB |
| 5,000 | 8,192 | 6,912,000,000 B | 343,102,976 B | 104 / 480 | 15.34 GiB |
| 5,000 | 65,536 | 6,912,000,000 B | 1,856,067,072 B | 104 / 480 | 13.66 GiB |

The full accepted-prefix fingerprints and GDN dumps were byte-identical between
8K and 64K context at each cache capacity, across all three repetitions. The
cache capacities produced different GDN, tail, pooled, pooled-full and KV
fingerprints at both context sizes; PLE, MTP, stale and dead fingerprints
matched. The first GDN difference was at layer 3. The 3,000-versus-5,000
comparison changed 27,506,109 of 29,417,472 float32 values (93.50%), with
1.659% global relative L2; the maximum per-layer relative L2 was 3.130% at
layer 14. Cache hits differed reproducibly alongside this state change, but
this experiment does not establish that hit/miss selection causes the numeric
difference.

This evidence isolates the observed state shift to cache capacity for this
prompt and request shape; configured context reservation did not change the
committed state. It does not establish which state is more accurate, task
quality, or a performance effect. Do not infer correctness from the shared
output token or promote a cache default. No timings or energy comparisons were
collected; clocks were observed dynamically.

As an operator-level cross-check, the standalone current CUDA
`s2_expert_grouped_parity --selftest` target rebuilt and passed under the
six-GiB supervisor. Its synthetic Q2_0 fixtures covered host-count and
device-count hit paths, mixed-precision activation scales, multi-token/window
hits, and alignment fallbacks. Every case was bitwise identical to the prior
kernel and passed the independent double-precision row reference (worst
reported error `1.10e-7` of sum-of-absolute-terms); the test recorded zero
failures and 24.60 GiB minimum host availability. This validates the isolated
grouped hit operator on its synthetic contract, not the full model's
hit/miss-combine path or the cross-capacity state result. The build and test
supervisor records are in `cuda-hit-parity-build-supervisor/` and
`cuda-hit-parity-supervisor/`; the test binary SHA-256 is
`9c86664c388ca66e130cbf531af17a85e1aac4ea0580c47a017a7f890d4969cd`.

`campaign.py`, `runner.py` and `analyze.py` preserve the randomized process
matrix, exact commands, state fingerprints and comparison. Raw request logs,
owner summaries, tegrastats and supervisor memory/clock samples are under
`campaign/`. Large GDN dumps remain in ignored `build/integration/` and their
hashes are retained in `factorial-summary.json`. No model or build artifact is
stored in Git.

Reproduce from the repository root with the local integration environment:

```sh
python bench/results/2026-10-12-phase3-q2-cache-context-state/campaign.py \
  --config bench/results/2026-10-12-phase3-q2-cache-state-diagnostic/config-cache3000.json \
  --engine build/integration/candidate/strata \
  --output /tmp/q2-cache-context-state \
  --python /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  --cache-values 3000 5000 --context-values 8192 65536 --repetitions 3 \
  --seed 202610126
python bench/results/2026-10-12-phase3-q2-cache-context-state/analyze.py \
  --campaign /tmp/q2-cache-context-state/campaign.json \
  --output /tmp/q2-cache-context-state/factorial-summary.json
```

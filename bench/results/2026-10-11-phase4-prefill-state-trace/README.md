# Prefill chunk accepted-state trace — Orin — 2026-10-11

This correctness-only experiment compares `--prefill 32` and `--prefill 128`
on the same 1,069-token historical-repeat prompt with an eight-token output cap.
Both configurations use the current IQ1_M Coder pack, MTP runtime, 4,096
context, fixed 5,000 max-blob-equivalent cache budget, one pool worker,
`STRATA_PREFILL_CPU_SHARE=0`, and prompt-cache size 6. Each process uses the
accepted-prefix harness's distinct same-length warmup. Two independent
processes per chunk ran under the six-GiB physical-availability supervisor.

All four measured requests completed eight tokens, and both chunk settings
produced the same token IDs:
`32, 6165, 11036, 1928, 1472, 264, 25924, 11`. Within each chunk setting,
both runs matched at every accepted-prefix state fingerprint, each of the 36
GDN layer hashes, and the output hash. Minimum `MemAvailable` was 8.47 GiB for
chunk 32 and 8.40 GiB for chunk 128.

The two settings first share a committed boundary at `L=1069`, immediately
after output token 32. At that boundary, their aggregate state hashes differ
for GDN, PLE history, QSA tail/pooled state, KV, MTP, and the dead/pooled-full
QSA fields. The stale-KV and `ple_prev` values match. **All 36 per-layer GDN
hashes differ at this boundary; ordinal 0 is the first differing slice.** The
full output token sequence remains equal, while accepted commit grouping differs:
chunk 32 commits 1/2/2/2/1 tokens; chunk 128 commits 1/2/4/1.

This establishes a deterministic, chunk-size-dependent bitwise state difference
for this prompt, even with CPU prefill sharing disabled. It does not quantify
float error or establish whether the resulting state difference exceeds an
acceptable task-level quality budget. No prefill default is promoted. A numerical
state-difference measure and held-out quality test remain necessary before
considering a behavior change.

The ordinary accepted-prefix traces are in `chunk32/` and `chunk128/`; the
per-GDN localization reruns are in `chunk32-gdn/` and `chunk128-gdn/`. Each
contains the server configs, API request, engine log, accepted-prefix trace,
and supervisor telemetry. `analysis.json` contains the four parsed traces and
the first-boundary comparison. The binary SHA256 is
`3fc0f58108c14e5e33bcfbf1092f1b377b132451ae77305878ca406f70d397f1`. Model,
pack and MTP files remain under `~/models/`.

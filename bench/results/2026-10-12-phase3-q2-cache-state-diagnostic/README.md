# Q2_0 cache-capacity persistent-state diagnostic — Orin — 2026-10-12

This diagnostic followed the differing GDN/state fingerprints in the 32K
Q2_0 cache screen. It held the model, tokenizer, prompt, context, prefill,
workspace reserve, `--mmap-experts`, `STRATA_PREFILL_CPU_SHARE=0`, pageable
staging and verifier path constant while changing the fixed expert cache from
3,000 to 5,000 slots. The current candidate SHA-256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`; the
Q2_0 model revision is `5348543e0147355ac9cbcb031184a3546350988e`.

For the same exact 512-token prompt (SHA-256
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`), two
independent processes per cache size produced the same state fingerprints
within each setting, but the 3,000- and 5,000-slot fingerprints differed.
Both emitted token ID 32. A third run per cache size with `--spec 4` retained
the same per-cache fingerprint, so increasing the verifier window did not
remove the result. All runs passed the six-GiB supervisor; minimum host
availability ranged from 17.90 to 18.20 GiB at 3,000 slots and 15.33 to 15.65
GiB at 5,000 slots. Every 512-token run used context 544, prefill 512, one
output token, prompt cache 6, a 3,072 MiB workspace reserve and CPU prefill
sharing disabled. These were correctness diagnostics, not timing comparisons.

The verifier's first FP32 logit row was also bit-identical across two
processes within each cache size, but every logit differed across sizes. Both
selected token 32 and shared the top 10 tokens. The cross-cache relative L2
logit difference was 2.72%, with symmetric KL values `6.87e-4` and `6.96e-4`.
The reported expert-cache hit counts were 55/480 and 112/480; reported
file-tier traffic was 587.5 and 508.7 MB, respectively. These counters show
that cache size changed the decode placement/miss pattern, but do not identify
the cause or measure physical disk traffic.

Two full float32 GDN comparisons were made from dumps preserved under ignored
`build/integration/phase3-q2-cache-state-diagnostic/`. The 512-token request's
post-request state differed in 94.28% of values, with 1.114% relative L2. A
second pair used the exact first 511 token IDs of the 512-token prompt and
compared state at accepted length 511; this avoids regenerating a different
prefix for a 511-token target. It differed in 93.50% of values, with 1.659%
relative L2. Layer 0 matched exactly in both comparisons; the prefix dump's
first large layer divergence was layer 3. The stored JSON comparisons and
dump SHA-256 values are in `gdn-comparison.json`,
`prefix-gdn-comparison.json` and `dump-manifest.json`.

The evidence establishes a repeatable cache-capacity effect on this decode
state/logit path, not whether the difference is acceptable or which component
causes it. Matching output text or argmax is insufficient to claim state
parity. Do not promote a cache default or infer quality from these diagnostics;
trace the expert-hit/miss compute path and qualify task output separately.
The attempted `--spec 1` control is retained as unsupported setup evidence:
the native pack rejects `--spec` values below 2 before model execution.

`prefix_state_runner.py` and the per-cell configs preserve the reproduction
commands and flags. Raw engine logs, `workload.json`, supervisor telemetry and
clock samples are retained in each cell directory. Large GDN/logit binaries
are deliberately kept in ignored `build/integration/`; their paths, sizes and
hashes are recorded in `dump-manifest.json`. No model or build product is in
Git. Clocks were observed without control; energy was not measured.

## CPU-order reduction follow-up

The opt-in `--expert-cache-cpu-order` path was then run once at each capacity
against the exact first 511 token IDs of the prompt. Both passed the six-GiB
supervisor, selected token 271, and had 19.39 GiB (3,000 slots) and 16.88 GiB
(5,000 slots) minimum host availability. Cache hits were 68/480 and 104/480.
The full 29,417,472-float accepted-prefix GDN dumps were byte-identical to the
corresponding default-path dumps at each capacity. The two capacities still
differed by 1.659% relative L2, with the first material layer divergence at
layer 3. Thus this reduction-order toggle does not explain the observed
capacity effect in this prompt; the hit/miss path and other capacity-dependent
effects remain unisolated. This one-run-per-setting check is diagnostic, not a
default-policy or performance result. The CPU-order cross-capacity comparison
is in `cpu-order-gdn-comparison.json`; raw dump hashes are added to
`dump-manifest.json`.

## Prefill-chunk × cache-capacity state screen

A randomized 2 × 4 screen crossed 3,000/5,000 expert-cache slots with prefill
chunks 64/128/256/512. Each cell used two fresh supervised processes on the
same exact first 511 token IDs, followed by one generated token. All 16 runs
passed the six-GiB floor (minimum host availability 15.57 GiB), selected token
271 and had bit-identical GDN dumps across the two process repeats within each
cell. This shows the state differences are repeatable for these configurations.

Full tensor comparisons found 2.19–3.30% relative L2 between chunk sizes at
fixed cache capacity. At each chunk size, the 3,000/5,000-slot states differed
by 1.66–2.29% relative L2. Chunk-size differences first exceeded `1e-4`
per-layer relative L2 at layer 1; cache-size differences first exceeded it at
layer 3. Both factors therefore affect accepted-prefix GDN state even though
this one-token output remained the same. `prefill-cache-factorial.json` records
the cell results, repeat hashes and 10 pairwise tensor comparisons; the full
per-layer comparisons are separate JSON files. Raw GDN dumps remain ignored
under `build/integration/` and are listed in `dump-manifest.json`.

The screen does not establish that the state deltas are acceptable, identify
the responsible operator, or measure task quality. Each cell has two repeats,
one prompt and one generated token; clocks were dynamic and energy was not
measured. Keep prefill chunk and cache capacity jointly qualified, and do not
promote a profile based on matching this token alone.

The same 16 logs also give consistent owner requests in both repeats. The
prefill owner peak grew from 197,201,152 bytes at chunk 64 to 350,079,744 bytes
at chunk 512 (145.8 MiB); the 128/256 peaks were 214,533,888/251,841,280 bytes.
The expert-cache owner requested 4,147,200,000 bytes at 3,000 slots and
6,912,000,000 bytes at 5,000. Instrumented device requested-live peaks ranged
from 6,017,027,072 to 8,934,705,664 bytes; host owner peaks were 354,492,280
bytes. All logs had 304 allocation and 303 free events, with the expected
1,485,606,400-byte weight arena remaining until process exit. These are unique
requested owner payloads at instrumented sites, not physical backing totals;
CUDA graph/driver-private bytes remain outside this trace. See
`prefill-cache-owners.json`; host availability and tegrastats are retained per
run.

## Sixty-four-token output follow-up

To check whether the state differences changed the immediate output sequence,
the same 511-token prompt was run for 64 greedy tokens at both endpoints of
the chunk/cache screen: chunks 64/512 × caches 3,000/5,000, with two fresh
processes per cell. All eight requests returned 64 tokens, and every token
sequence was identical (SHA-256
`b10c76bf98fb70ceeaea81138d5a5034c50470900e2a874d319a525d4924f2f4`). Each
run recorded 64 accepted-prefix commits; fingerprints were byte-for-byte
repeatable between processes within each cell, but differed from the
3,000-slot/chunk-512 control at every commit when either factor changed. The
lowest `MemAvailable` was 15.57 GiB, above the supervisor floor. Raw token IDs,
accepted-prefix logs, commands and per-run telemetry are retained in the cell
directories; `long-output-comparison.json` summarizes them.

This establishes same-sequence output for one exact prompt and greedy 64-token
continuation despite persistent-state differences. It is not an independent
quality oracle, a held-out prompt result, or a long-context quality test. No
cache or prefill default is promoted. The initial attempts with context 576
were rejected by request validation because the runtime reserves eight extra
positions; one queued attempt was interrupted after a result-directory
collision. Those setup records are retained and excluded from the valid
comparison in `long-output-failed-attempts.json`.

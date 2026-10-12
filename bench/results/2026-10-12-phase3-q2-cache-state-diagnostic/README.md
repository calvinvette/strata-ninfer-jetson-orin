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

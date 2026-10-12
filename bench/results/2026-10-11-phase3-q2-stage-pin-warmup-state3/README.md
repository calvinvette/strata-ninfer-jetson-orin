# Q2_0 stage backing: traced warmup/state follow-up

This three-pair follow-up uses the same 172-token/64-output warmup before each
512-token/64-output measured request, while tracing token IDs, persistent state
and stage-buffer owners. It is correctness evidence only; its timing values are
not used.

Two pairs passed: both arms had the same warmup completion hash, same measured
token IDs, all nine persistent-state fingerprints, and the expected separate
pageable/pinned owner with 353,894,400 requested bytes. In pair 1, the warmup
completion hashes differed although both produced 64 tokens. The measured
64-token outputs still matched, but five state fields differed: GDN, tail,
pooled, full pooled and KV. The result correctly failed and the supervised
process exited nonzero. It is retained; it is not excluded from the 2/3 pass
count.

This points to an interaction between warmup output variation and the later
measured state, or another run-to-run numerical difference. The present capture
does not isolate the cause. It does show that equal measured text alone is not
enough to claim persistent-state parity after a warmup. The stage timing
confirmation is consequently diagnostic only. The parity harness now compares
warmup completion hashes and marks a divergent warmup as a failed pair.

All three process groups stayed within the 28-GiB cap and six-GiB physical
availability guard; minimum host `MemAvailable` was 21.15 GiB and no OOM
occurred. Raw arm logs, supervisor samples and tegrastats are retained under
`pair-*`. Model artifacts remain under `~/models/`.

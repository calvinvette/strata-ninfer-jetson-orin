# ISTA IQ3_S `is_prime` service and state check — Orin — 2026-11-05

Two fresh supervised Strata/strict-NInfer pairs used the actual ISTA-DASLab
Qwen3.8-Flash-Next IQ3_S GGUF shards, matching `iq3-s-pack`, and the same static
512-slot profile as the shorter `is_even` experiment. Each arm received the
same 50-token prompt and used MTP-2, a 512-token context, zero temperature,
state hashing and accepted-prefix tracing.

All four arms generated the same 91 token IDs and passed the independent
restricted-AST `is_prime(n)` oracle on 11 cases from −7 through 997. Across
both pairs, Strata and NInfer each reproduced their own token IDs and state at
every shared endpoint. Within both Strata/NInfer pairs, state hashes first
differed at token 32 in the `stale` field; the first live difference was at
token 33. The two verifiers exposed 80 shared accepted-prefix endpoints, of
which 53 had at least one state-field difference. At the final state, GDN,
PLE, tail, pooled, pooled-full and KV hashes differed. Thus matching generated
code and passing the executable oracle do not establish persistent-state
parity; the divergence was repeatable for this model, task and profile.

Teacher-forced scoring of this same sequence covered all 140 next-token
targets. The score records matched at the logger's precision (target
log-probabilities to nine decimals, top-k values to six), with 100% top-1
agreement and top-10 overlap. This shows that observed state divergence did not
change these recorded answer scores, but does not establish bitwise-equal logits
or a general tolerance. See the [scoring report](../ista-is-prime-scoring/README.md).

The first harness attempt stopped after Strata generated the answer because
the restricted oracle did not yet allow the ordinary `for range(...)`, `int`
and exponentiation syntax in the returned function. NInfer was not run in that
attempt. The test harness was extended to allow those specific constructs
while keeping builtins disabled and limiting callable names to `int` and
`range`; the captured code passed all 11 cases, then both full pairs passed.
This first attempt is retained in the raw supervisor directory and recorded as
a harness failure in [`results.json`](results.json), not as a model failure.

Minimum available RAM was 19.74 GiB and 19.64 GiB across the two pairs; sampled
swap peaked at 1.79 and 1.83 GiB. The existing cgroup OOM-kill count
stayed at one. Clocks were observed dynamically, EMC readback was denied, and
energy was not measured. These sequential traced requests are correctness
checks; timing values are not performance evidence. Model, pack, binary and
profile hashes, each run's tokens and all captured prefix states are in
[`results.json`](results.json). Raw logs and telemetry remain in adjacent local
run directories.

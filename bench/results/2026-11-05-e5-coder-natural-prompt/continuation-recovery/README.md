# Coder same-engine continuation and recovery

Date: 2026-11-05. Jetson Orin AGX, CUDA 12.6. This checks the held-out
`is_prime` task as three requests on one engine process: 32 generated tokens,
a continuation of 32, then recovery for up to 32 more. Both runs use the same
50-token prompt, static 391-slot Coder IQ1_M profile, 4,096-token context and
`STRATA_PREFILL_CPU_SHARE=0`. The completed function is checked against the
same 11-case restricted-AST oracle as the held-out task report.

## Results

All Strata and strict-NInfer arms produced the same 89 token IDs across the
three requests and passed all 11 function cases. The split was 32, 32 and 25
tokens, with the third request ending normally. The behavior depends on state
capture:

| Capture | MTP | Fresh backend pairs | Output and quality | Request-boundary state | Accepted-prefix state |
|---|---:|---:|---|---|---|
| Per-token trace | 2 | 1 | Exact IDs; both pass | Differed after each request | First mismatch at token 25 in request 1; at token 5 in continuation; at token 4 in recovery |
| Per-token trace | 4 | 1 | Exact IDs; both pass | Differed after each request | Same first-mismatch locations as MTP-2 |
| Final-only hashes | 2 | 2 | Exact IDs; both pass | Matched at all three request boundaries in both pairs | Not captured |

In the traced runs, the number of mismatching shared-prefix checkpoints was
2/28 in the initial request, 25/28 in the continuation, and 14/23 in recovery.
MTP-2 and MTP-4 had the same token stream and the same mismatch pattern.
In the two final-only MTP-2 pairs, all 11 state fields matched at all three
request boundaries across backends, and each backend reproduced the same
states and output in the second fresh pair. The full output token SHA-256 was
`70ddb7d7606fd66fb195c8484b701d3fe3d5e16854467d2755977b6dd6b7dd6b5cf` in
every arm.

This supports trace/scheduling sensitivity as the explanation for this
sequence's observed state mismatch: the output and quality are unchanged,
traced prefixes diverge, and final-only request-boundary hashes match and
repeat. It does not establish the exact cause of the observer effect or prove
intermediate states are equal when tracing is disabled. The traced and
final-only runs are kept separate; their state results must not be pooled.

## Resource and identity record

The exact model shard names, sizes and SHA-256 values, binary/profile hashes,
prompt hash, request states, trace mismatch counts, and memory summaries are in
[`results.json`](results.json). Both model shards remain under `~/models`.
Minimum sampled available RAM was 20.95 and 21.03 GiB in the trace runs, and
20.81 and 20.74 GiB in the final-only runs. Swap peaked at 1.38, 1.23, 1.22
and 1.22 GiB, respectively. The pre-existing cgroup OOM-kill count remained
one. The traced runners exit nonzero because their accepted-prefix parity
check detects the state mismatch; the supervisor had adequate memory and the
completed task passed its output-quality oracle. Final-only runs passed both
the supervisor and state checks. No performance conclusion is drawn from these
sequential diagnostic runs.

Reproduce a final-only MTP-2 pair:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/is-prime-continuation-final-only-supervisor \
  --sample-clocks --timeout 3600 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_continuation_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/is-prime-continuation-final-only-run 2 final
```

This adds bounded same-engine continuation and recovery evidence for the
static Coder profile. Cancellation, broader task/context behavior, and useful
performance remain open.

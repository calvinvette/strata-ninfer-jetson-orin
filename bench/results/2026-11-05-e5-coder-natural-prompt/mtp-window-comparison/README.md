# Coder IQ1_M MTP-2 and MTP-4 state check

Date: 2026-11-05. Jetson Orin AGX, CUDA 12.6. This compares the supported
MTP-2 and MTP-4 settings on the same tokenizer-exact 512-token active-ticket
retrieval prompt, 4,096-token context reservation, and static 391-slot Coder
IQ1_M expert profile. Each mode ran two fresh Strata/strict-NInfer pairs.

## Results

Both MTP settings passed in all four backend pairs. Every request returned the
exact answer `73192` with token IDs `[22, 18, 16, 24, 17, 248046]`. Every pair
matched all 11 final-state fields across backends. The output and all state
fields were also identical between MTP-2 and MTP-4 for each backend, and
reproduced in both fresh pairs. Each arm offered and accepted two speculative
draft tokens. The MTP-4 engine initialized its six-token verifier window.

| Mode | Fresh pairs | Cross-backend answer/state | Accepted drafts per arm | Minimum available RAM | Peak swap |
|---|---:|---|---:|---:|---:|
| MTP-2 | 2 | Exact in both pairs | 2 / 2 | 21.02, 21.06 GiB | 1.41, 1.26 GiB |
| MTP-4 | 2 | Exact in both pairs | 2 / 2 | 21.16, 21.22 GiB | 1.39, 1.41 GiB |
| MTP-off | Unsupported | The native IQ pack rejects `--spec 0` | — | — | — |

The MTP-off request exited before engine readiness or model loading. The
current native IQ pack argument contract requires `--spec T` with `T >= 2`.
This means MTP-off was not available for this model/runtime configuration;
it is not a failed inference result.

## Scope and reproduction

The exact prompt hash, model shard sizes/checksums, executable/profile hashes,
per-pair state fingerprints, draft counts and memory summaries are in
[`results.json`](results.json). The pre-existing cgroup OOM-kill count stayed
at one in all four successful pair runs. Prefix-by-prefix state, cancellation,
recovery and performance were not measured in this comparison. The request
order was Strata then NInfer, and the short task is unsuitable for a throughput
claim.

Reproduce one MTP-4 pair from the integration worktree:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/retrieval-512-mtp4-supervisor \
  --sample-clocks --timeout 1800 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_retrieval_final_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/retrieval-512-mtp4-run 512 4096 - 4
```

This qualifies bounded MTP-2/MTP-4 answer and terminal-state behavior for one
Coder IQ1_M task/profile. It does not establish broader MTP quality, rejection
isolation, continuation/recovery or useful performance.

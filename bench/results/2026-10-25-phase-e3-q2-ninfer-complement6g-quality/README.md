# 6-GiB staged Q2_0 held-out functional check

This check uses the held-out 512-token retrieval/arithmetic workload from the
E5 Q2_0 functional evidence. The expected response is:

```text
EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768
```

The Strata control and strict NInfer arm used the same 3,000-slot cache, 6-GiB
resident budget, 3-GiB workspace reserve, 8K context cap, and staged route
(`--pcie-frac 1.0`). Adaptive swaps were disabled. Both arms returned the exact
expected response and identical 47 generated token IDs. Persistent state did
not match: fingerprints differ for GDN, tail, pooled, pooled-full, and KV.
Accordingly, the check failed the state-parity gate. This does not assert that
the visible answer is incorrect; it means equivalence of the resulting runtime
state has not been demonstrated.

| Metric | Strata | Strict NInfer |
| --- | ---: | ---: |
| Prompt tokens | 512 | 512 |
| Generated tokens | 47 | 47 |
| Prompt time | 31.668 s | 31.127 s |
| Decode time | 8.339 s | 8.525 s |
| Offloaded entries | 4,528 | 4,536 |
| Exact expected answer | pass | pass |
| Token IDs equal across arms | yes | yes |
| Final persistent state equal | no | no |

This is one task and not broad model-quality qualification. Because state
parity failed, the favorable 6-GiB TTFT screening result does not proceed to
seven-pair performance confirmation or profile promotion. Raw output is in
[`evidence/results.json`](evidence/results.json); the supervised invocation
and resource telemetry are alongside it.

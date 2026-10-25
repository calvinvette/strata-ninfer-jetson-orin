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

## State-difference follow-up

The final GDN arrays were compared directly at `L=558`: 26,711,062 of
29,417,472 values differed (90.80%), with global relative L2 0.02396, RMS
absolute delta 0.00599, and maximum absolute delta 0.6991 at GDN layer 25.
Layers 0–2 were bit-identical; layer 3 was the first with a nonzero delta
(relative L2 approximately `1.2e-7`). A targeted verifier capture at generated
position 557 in model layer 3 found identical inputs, routes/weights, expert
parts, shared output and combined output between backends. This capture does
not explain the GDN difference: it sampled one generated position, while the
state aggregates the full 512-token prompt and continuation. It therefore
cannot rule out earlier prompt-position differences or attribute the first
GDN delta to the staged expert kernel. Numeric GDN analysis and compact
position-557 captures are retained in `gdn-dump/gdn-diff.json` and
`moe-layer3-pos557/` respectively. The large raw GDN arrays and service logs
remain local and are not committed.

A second targeted capture at the last prompt position (511), model layer 1,
also found identical inputs, routes/weights, expert parts and outputs. These
two exact sampled boundaries do not account for the accumulated state delta;
other prompt positions and layers remain unsampled.

A multi-position layer-3 verifier capture sampled generated positions 512,
520, 530, 540 and 557. The first sampled difference was at position 520:
input, route IDs and route weights matched, while expert 94 (route rank 5)
differed in 1,538/2,560 output values (relative L2 `7.15e-4`, max absolute
delta `4.55e-5`). The combined MoE output differed in 1,538/2,560 values
(relative L2 `1.37e-4`); shared output remained exact. The other four sampled
positions were bit-identical. Positions 513–519 were not sampled, so position
520 is not proven to be the first divergent token. This isolates a same-input,
same-route expert arithmetic difference in one sampled layer-3 row; it is
consistent with the final-state difference but does not alone prove its full
causal path. The multi-position files and per-expert comparison are in
`moe-layer3-generated/`.

## Standalone grouped-kernel replay

The captured layer-3 / expert-94 activation was replayed with the existing
`ninfer_q2_expert_parity` binary and the same model shard. Its scalar
F32-input Q2_0 D3/D4 implementation matched the independent FP64 reference
closely (relative L2 `2.05e-7`, maximum absolute error `1.49e-8`). The grouped
resident route, which quantizes the activation to Q8_1 and compares NInfer
against Strata, returned relative L1 `6.71e-4`; this fails the harness's
`2.0e-4` limit. Thus the grouped numerical difference reproduces outside the
service with the same expert weights and activation; the scalar pass does not
qualify the grouped service path. The parity command also measured one-entry
NInfer/Strata at 0.978×, while grouped 64- and 128-token runs were 1.108× and
1.121×, respectively. These are local operator diagnostics rather than
end-to-end results. The harness exited nonzero because the grouped parity
checks failed. Its output and supervisor record are in `expert94-parity/`.

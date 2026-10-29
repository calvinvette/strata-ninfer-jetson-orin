# E6 accepted-prefix GDN order-balanced repeats

Six paired 160K Q2_0 retrieval captures compare Strata-first/NInfer-second
with NInfer-first/Strata-second, three pairs per order. Every pair produced the
same answer, 47 token IDs, and residency fingerprint across engines, but every
pair failed final persistent-state parity. Each capture compared 36 GDN layers
at prompt boundary 163840 and generated positions 163862 and 163885.

## Cross-backend first material delta by pair

“None” means all layers remained below relative L2 `1e-6`. Values are the
median and range of relative L2 at the first material layer within each order.

| Arm order | Position 163840 layer / rel-L2 | Position 163862 layer / rel-L2 | Position 163885 layer / rel-L2 |
| --- | --- | --- | --- |
| Strata then NInfer (n=3) | 12, 12, none / median `1.1694e-4`, range `0–1.1694e-4` | 4, 4, none / median `3.2549e-3`, range `0–3.2555e-3` | 4, 4, 44 / median `2.8286e-3`, range `6.5978e-4–2.8287e-3` |
| NInfer then Strata (n=3) | none, none, 12 / median `0`, range `0–1.1694e-4` | 8, 4, 8 / median `3.2368e-3`, range `3.2365e-3–3.2555e-3` | 5, 4, 4 / median `2.9846e-3`, range `7.4242e-4–3.1965e-3` |

## Interpretation and next action

The prompt-boundary state stayed below threshold across engines in four of six
pairs (two of three in NInfer-first and one of three in Strata-first). This may
indicate an order interaction, but the sample is small and same-backend
run-to-run state drift is material. At generated positions, the relative-L2
ranges overlap across orders, and the first differing layer is not stable.
Therefore order and backend causation are not established. Matching text,
token IDs, and residency is insufficient to pass the persistent-state gate.
Do not change backend arithmetic based on this evidence.

Next, isolate process-history and run-to-run variation with a small,
pre-registered matrix of matched single-backend repeats and process
initialization/order controls. Continue to require direct accepted-prefix
persistent-state parity before claiming correctness or pursuing localized
operator changes.

Per-pair reports: [Strata-first pair 1](../gdn-commit-all-3pos/README.md),
[Strata-first pair 2](../gdn-commit-all-3pos-repeat/README.md),
[Strata-first pair 3](../gdn-commit-all-3pos-strata-first-repeat2/README.md),
[NInfer-first pair 1](../gdn-commit-all-3pos-reversed/README.md),
[NInfer-first pair 2](../gdn-commit-all-3pos-reversed-repeat/README.md),
[NInfer-first pair 3](../gdn-commit-all-3pos-reversed-repeat2/README.md).

Detailed binary captures, comparator JSON, logs, and supervisor samples remain
local-only. No performance conclusion is drawn from these correctness runs.

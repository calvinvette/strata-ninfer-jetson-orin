# Reversed-order accepted-prefix GDN comparison

This paired the same 160K Q2_0 retrieval and all-layer accepted-prefix capture
as the [Strata-first controls](../gdn-commit-all-3pos-repeat/README.md), but
ran strict NInfer first and Strata second using
`--reverse-staged-backends`. The prompt, model, context, cache settings and
capture positions (163840, 163862, 163885) were unchanged.

Both arms returned the exact answer, all 47 matching token IDs, and the same
residency fingerprint (`a02fd81e...ddf7`). Final `gdn`, `tail`, `pooled`,
`pooled_full`, and `kv` state fields differed, so the harness correctly
reports a state-parity failure. The run took 3,243.1 seconds. Minimum available
memory was 7,198,883,840 bytes (6.70 GiB), above the 6 GiB guard. Clocks were
observed but not controlled; energy was not measured.

## Accepted-prefix state

| Accepted position | First exact difference | First layer at rel-L2 >= 1e-6 | Relative L2 there |
| ---: | ---: | ---: | ---: |
| 163840 (prompt boundary) | none; all 36 layers exact | none | `0` |
| 163862 | model layer 4 (rounding scale) | model layer 8 | `3.237e-3` |
| 163885 | model layer 4 (rounding scale) | model layer 5 | `7.424e-4` |

This differs from the two Strata-first pairs, whose first material
cross-backend difference appeared at layer 12 at the prompt boundary and
layer 4 at both generated positions. Reversing arm order therefore coincides
with a different observed onset in this one pair, including bitwise prompt
boundary parity. Because this is one reversed-order trial and the earlier
same-order runs showed cross-run state crossover, it is not yet evidence that
order caused the change. Repeat the reverse order with the same settings, then
compare both orders at the same accepted prefixes before assigning a cause.

The paired harness failed only its expected persistent-state parity check;
see `run/results.json`. Raw GDN records, comparator JSON, logs and supervisor
samples remain local-only in `run/` and `supervisor/`. Models remain in
`~/models/strata-orin-validation/`.

The reverse-order capture was repeated. Prompt-boundary parity remained within
`1e-6`, but the generated-prefix material onset moved from layers 8/5 to layer
4 at both positions. Same-backend run-to-run differences also remain. See the
[repeat report](../gdn-commit-all-3pos-reversed-repeat/README.md).

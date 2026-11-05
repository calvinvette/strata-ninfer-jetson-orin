# Held-out longer Coder task and accepted-prefix state

Date: 2026-11-05. Jetson Orin AGX, CUDA 12.6. This follow-up checks the
IQ4_NL reduction-order correction on a longer, executable Coder task. It is
functional and state evidence only; the request logs enable prefix hashing and
MTP, so their timing fields are not a performance comparison.

## Task and result

The same 50-token chat prompt requested only a Python `is_prime(n)` function.
Both Strata and strict NInfer generated the same 89 token IDs and the same
function. The generated function passed 11 checks covering negative input, 0,
1, small primes, composites and a three-digit prime. The runner validates and
executes only a restricted arithmetic subset of Python AST nodes, with builtins
disabled. This adds a longer task than the earlier 21-token `is_even(n)` check;
it does not establish broad code quality.

MTP committed groups of different sizes: the first pair recorded 85 Strata
versus 80 strict-NInfer verifier commits, each covering the same 89 output
tokens. A second pair recorded 80 commits on each backend, again with the same
89-token stream. At their shared cumulative-token endpoints, both pairs first
differed at endpoint 25 in `stale` only. This field hashes KV cells from the
live length to the end of the current QSA page; the source labels them stale
and unused unless read. The first non-stale difference occurred at endpoint
37 in the first pair and endpoint 38 in the repeat. Final state differed in
both pairs.

A separate 42-token repeat with per-layer GDN and QSA hashing enabled matched
between backends at all 38 shared state endpoints, including every per-layer
hash. Its token stream exactly matched the first 42 tokens of the longer
requests. The heavier diagnostic did not reproduce the live-state split. The
two ordinary pairs also differed in MTP draft acceptance counts, despite
identical generated token IDs. These results show the live-state difference is
not yet localized reproducibly; instrumentation and verifier scheduling are
possible influences, not proven causes. The stale-only difference does not
establish that later drift is harmless.

| Evidence | Result |
| --- | --- |
| Generated output | 89/89 token IDs equal |
| Functional cases | 11/11 pass on each backend |
| Generated output | Same 89 token IDs and same tested function in both ordinary pairs |
| Accepted-prefix commits | 85/80 in pair 1; 80/80 in pair 2; each covers the same 89 tokens |
| First full hash difference | Token endpoint 25 in both pairs, `stale` only |
| First non-stale difference | Token endpoint 37 in pair 1; endpoint 38 in pair 2 |
| 42-token per-layer trace | All 38 shared endpoints and all GDN/QSA layer hashes equal |
| Final state | Different in both ordinary pairs |
| Supervisor | All three runs passed; minimum available RAM 20.91–21.02 GiB |
| Swap / OOM | Sampled machine swap usage 1.07–1.12 GiB; existing OOM-kill count stayed at 1 |

## Reproduction and limits

Run an ordinary functional/state pair from the repository root:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/is-prime-heldout-supervisor \
  --sample-clocks --timeout 1800 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_state_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/is-prime-heldout-run
```

The result records the model shard names and byte sizes, binary/profile hashes,
runtime options and aligned state comparison. Run the per-layer diagnostic with:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/is-prime-layer-state-supervisor \
  --sample-clocks --timeout 1800 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_layer_state_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/is-prime-layer-state-run 42
```

The captured binary SHA-256 is
`df8e666b8d19dbdc5f687826b4d7187783f4c91aaf5ba2037497a65823d4be98`; the
static expert-profile SHA-256 is
`c1e66c2e60ae8e7880befa303fb6bb79da1ccdd59895053eb95d433c648ef047`. Read-only
GPU clock samples varied from 306 to 1,300.5 MHz; EMC readback was denied.
Energy was not measured. The main evidence is in [`results.json`](results.json).

These runs do not resolve the inconsistent live-state divergence, define an
accepted state-drift tolerance, qualify other tasks or contexts, or show a
performance gain. Continue with lower-perturbation state localization and
distinct held-out task families. See the [ordinary-pair repeat](repeat-results.json)
and [42-token per-layer trace](layer-state-results.json). E5/E6/E7 remain open.

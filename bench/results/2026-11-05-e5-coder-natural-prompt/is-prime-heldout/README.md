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

MTP committed groups of different sizes: Strata recorded 85 verifier commits
and strict NInfer 80, each covering the same 89 output tokens. State was
therefore compared only at the 79 common cumulative-token endpoints. At endpoint
25, the only changed field was `stale`, which hashes KV cells from the live
length to the end of the current QSA page; the source labels those cells stale
and unused unless read. The first difference in other state fields occurred at
endpoint 37. Final state hashes also differ. Thus exact output tokens and task
behavior coexist with later live-state divergence; the stale-only difference
does not account for the later state delta or establish that it is harmless.

| Evidence | Result |
| --- | --- |
| Generated output | 89/89 token IDs equal |
| Functional cases | 11/11 pass on each backend |
| Accepted-prefix records | 85 Strata; 80 strict NInfer; same 89 token IDs |
| Common cumulative-token state endpoints | 79 |
| First full hash difference | Token endpoint 25, `stale` only |
| First non-stale hash difference | Token endpoint 37 |
| Final state | Different |
| Supervisor | Pass; minimum available RAM 21.02 GiB |
| Swap / OOM | Sampled machine swap usage 1.07–1.12 GiB; existing OOM-kill count stayed at 1 |

## Reproduction and limits

Run from the repository root:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-11-05-e5-coder-natural-prompt/is-prime-heldout-supervisor \
  --sample-clocks --timeout 1800 -- \
  python bench/results/2026-11-05-e5-coder-natural-prompt/run_is_prime_state_pair.py \
  bench/results/2026-11-05-e5-coder-natural-prompt/is-prime-heldout-run
```

The result records the model shard names and byte sizes, binary/profile hashes,
runtime options and aligned state comparison. The captured binary SHA-256 is
`df8e666b8d19dbdc5f687826b4d7187783f4c91aaf5ba2037497a65823d4be98`; the
static expert-profile SHA-256 is
`c1e66c2e60ae8e7880befa303fb6bb79da1ccdd59895053eb95d433c648ef047`. Read-only
GPU clock samples varied from 306 to 1,300.5 MHz; EMC readback was denied.
Energy was not measured. The main evidence is in [`results.json`](results.json).

This single held-out prompt does not resolve why live state first diverges at
token 37, define an accepted state-drift tolerance, qualify other tasks or
contexts, or show a performance gain. Continue by localizing the first live
state delta and repeating across distinct task families. E5/E6/E7 remain open.

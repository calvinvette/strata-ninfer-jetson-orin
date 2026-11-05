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
at all 38 shared state endpoints, including every per-layer hash. Its token
stream exactly matched the first 42 tokens of the longer requests. A further
full 89-token pair with prefix tracing sampled every eight tokens matched all
10 shared accepted-prefix snapshots, including all GDN/QSA layer hashes at
each sampled point and the final token. Most directly, two full runs with
accepted-prefix tracing disabled matched all 89 token IDs, the tested
function, and the complete final fingerprint including MTP and stale fields.
Each final-only pair also reproduced exact cross-backend state within its run.

In the two ordinary per-token trace pairs, the first non-stale differences were
at tokens 37 and 38. The exact same task and token stream had matching state
when checks were sampled every eight tokens or only after generation. The
per-token state helper calls `cudaDeviceSynchronize` and copies state to the
host; cadence and MTP grouping also varied between runs. This makes observer
or scheduling influence a plausible explanation for the tracing mismatch, but
does not prove its cause. Every-eight-token coverage also cannot rule out
transient between-check differences. The recorded stale-only mismatch does
not establish that later divergence is harmless.

| Evidence | Result |
| --- | --- |
| Generated output | 89/89 token IDs equal |
| Functional cases | 11/11 pass on each backend |
| Generated output | Same 89 token IDs and same tested function in both ordinary pairs |
| Accepted-prefix commits | 85/80 in pair 1; 80/80 in pair 2; each covers the same 89 tokens |
| First full hash difference | Token endpoint 25 in both pairs, `stale` only |
| First non-stale difference under per-token tracing | Token endpoint 37 in pair 1; endpoint 38 in pair 2 |
| Per-layer checks at stride 1 (42-token run) | All 38 sampled endpoints and all GDN/QSA layer hashes equal |
| Per-layer checks at stride 8 (full run) | All 10 sampled endpoints, final included, and all GDN/QSA hashes equal |
| Final-only state check | Two full pairs match all 11 final fingerprint fields |
| Supervisor | All six pairs passed; minimum available RAM 20.91–21.02 GiB |
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

For lower-interference final-state checks, append `--no-prefix-trace` after
the output directory. For sparse per-layer checkpoints, run the layer-state
helper with token limit `128` and trace stride `8`.

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

These runs strongly suggest that per-token state-hash instrumentation affects
the observed live-state result, but do not prove the cause or rule out transient
differences between sparse checkpoints. They do not define a general state
tolerance, qualify other tasks or contexts, or show a performance gain.
Continue with independent held-out task families and a lower-interference
accepted-prefix oracle. See the [ordinary pair](results.json),
[ordinary repeat](repeat-results.json), [42-token per-layer trace](layer-state-results.json),
[stride-8 trace](stride8-layer-results.json), and [two final-only pairs](final-only-results.json,
final-only-repeat-results.json). E5/E6/E7 remain open.

# E6 prompt-length and configured-capacity repeatability screen

This screen separates prompt length from configured `--max-context` as far as
the current controls allow. Each row is a fresh-process, same-backend repeat
of the held-out Q2_0 retrieval. Each pair produced the expected answer, the
same 47 generated token IDs, and the same residency hash. The state gate
requires exact final persistent-state parity; GDN captures compare all 36
layers at the prompt boundary and after generated-token offsets 22 and 45.

| Prompt | Configured capacity | Backend | Pair wall time | Min available RAM | Final state and sampled GDN | OOM kills |
| ---: | ---: | --- | ---: | ---: | --- | ---: |
| 2,048 | 8,192 | NInfer | 180.3 s | 11.44 GiB | exact / bitwise at all 3 positions | 0 |
| 2,048 | 8,192 | Strata | 180.1 s | 11.79 GiB | exact / bitwise at all 3 positions | 0 |
| 16,384 | 32,768 | NInfer | 476.7 s | 10.98 GiB | exact / bitwise at all 3 positions | 0 |
| 16,384 | 32,768 | Strata | 471.0 s | 11.16 GiB | exact / bitwise at all 3 positions | 0 |
| 16,384 | 262,144 | NInfer | 602.9 s | 7.30 GiB | final state differs; GDN drift | 0 |
| 16,384 | 262,144 | Strata | 608.5 s | 7.35 GiB | final state differs; GDN drift | 0 |
| 32,768 | 65,536 | NInfer | 792.0 s | 10.01 GiB | exact / bitwise at all 3 positions | 0 |
| 32,768 | 65,536 | Strata | 787.3 s | 10.08 GiB | exact / bitwise at all 3 positions | 0 |
| 32,768 | 262,144 | NInfer | 884.7 s | 7.00 GiB | final state differs; GDN drift | 0 |
| 32,768 | 262,144 | Strata | 890.1 s | 7.02 GiB | final state differs; GDN drift | 0 |

At 32K prompt length, both backends are bitwise repeatable with a 65,536
configured capacity, while both fail the final-state comparison with a
262,144 capacity. The same pattern appears at 16K: repeatable in the earlier
32,768-capacity fixture, but not in the 262,144-capacity repeat. This makes
configured capacity a strong candidate condition for the drift, rather than
prompt length alone. It is not yet causal evidence: there is one pair per
backend and condition, and the short-capacity 16K result came from a prior
fixture. Repeat matched capacity/length cells before assigning cause.

The large-capacity failures preserve answer, token IDs, and residency, but do
not pass exact persistent-state parity. Their supervisor `fail` status is the
expected correctness gate; each remained above the six-GiB available-memory
floor and recorded no OOM kills. The smaller-capacity pairs passed the state
gate. The 32K/65,536 controls also remained well above the floor. No clocks
were changed; energy was not measured. These are correctness and
repeatability observations, not performance claims.

**32K/262,144 replication:** a second same-backend pair reproduced the
large-capacity failure for both NInfer and Strata. Both again matched answer,
47 token IDs, and residency while final persistent-state fingerprints differed.
At the prompt boundary, both backends had the first sampled material GDN
delta at layer 22 with relative L2 `1.523e-3`; later sampled positions also
showed material drift. Pair runtimes were 876.1 s (NInfer, minimum available
RAM 7.21 GiB) and 883.4 s (Strata, 7.14 GiB), with zero OOM kills. This
reproduces the capacity-associated effect across both engines, although the
65K and 262K comparison still needs another matched 32K pair per capacity to
quantify run-to-run variability. Raw pair captures and comparator JSON remain
local-only.

Next, repeat both 16K capacity cells with identical capture settings, then add
another pair per 32K capacity cell and a capacity-matched length control where
memory permits. If the capacity interaction remains, inspect capacity-
dependent allocation/dispatch and state initialization before changing
backend math.

The 32K/65,536 measurements are in the local-only `32k-capacity-65536-*`
directories. Earlier 2K/16K controls and 262,144-capacity runs are in the
[prior screen](../2026-10-28-e6-q2-state-repeatability-length-screen/README.md)
and the ignored `fixed-capacity-262144/` directory. Raw captures, comparator
JSON, configs, logs, and supervisor samples remain local-only.

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

**16K/262,144 replication:** a second pair per backend also reproduced the
state failure. Both backends matched answer, all 47 token IDs, and residency,
while final persistent-state fingerprints differed. At positions 16,384,
16,406 and 16,429, the first sampled material GDN layers were 14, 2 and 2 for
both backends, with relative L2 `1.478e-5`, `1.479e-5` and `7.689e-6`.
Maximum layer relative L2 values at those positions were `0.0837–0.0921`,
`0.0920–0.0921`, and `0.0612–0.0614` respectively across the two backends.
Pair wall times were 609.3 s (NInfer, minimum RAM 7.19 GiB) and 606.9 s
(Strata, 7.13 GiB); neither recorded OOM kills. This reproduces the 16K
large-capacity failure for both implementations and its sampled GDN trajectory.
The shared onset/magnitude is a useful cross-backend clue, not proof of a
common root cause.

**Matched 16K/32,768 replication:** a second pair per backend under the same
capture settings was again exact in final persistent state and bitwise across
all GDN layers at positions 16,384, 16,406 and 16,429. Pair wall times were
489.6 s (NInfer, minimum RAM 10.96 GiB) and 484.3 s (Strata, 10.96 GiB), with
no OOM kills. Together with the repeated 16K/262,144 failures, this is a
matched-length capacity contrast reproduced across both backends. At 32K,
262,144-capacity failure also reproduced for both backends; the 65,536-capacity
exact result currently has one pair per backend. This supports configured
capacity as the leading condition in this screen, while the exact mechanism
and possible interactions with allocation/layout remain unresolved.

Next, add a second 32K pair at 65,536 capacity, then inspect capacity-driven
QSA allocation/layout, selection and attention dispatch that can propagate
into later GDN state. Use focused controls before changing backend math.

**Layer-2 expert-owner diagnostic:** route ownership was captured at prompt
position 16,383, model layer 2, at 32,768 and 262,144 configured capacity in
MTP-off and MTP-4 arms. All four captures had the same routed IDs:
`372, 357, 5, 114, 89, 59, 222, 84, 130, 12`. Experts 372, 357, and 222
were CPU-owned; 5, 59, and 12 were resident-GPU-owned; 114, 89, and 84 were
PCIe-staged GPU work. Expert 130 changed owner: PCIe-staged GPU at 32,768 and
CPU at 262,144. Its route rank was 8 in both captures. The earlier layer-2
expert-part delta (`1.064e-7` relative L2, maximum absolute `7.45e-9`)
therefore compares different execution tiers. NInfer handles the staged GPU
group; the CPU miss uses Strata's CPU expert implementation. This is not an
NInfer-kernel-only capacity comparison.

Startup logs show the corresponding pinned-expert change: 32,768 runs mapped a
6.00 GiB pinned expert complement and reported 11.2–11.4 GiB shared RAM
available after loading. At 262,144, the pinned complement was 3.97–4.11 GiB
and shared RAM available was 7.44–7.61 GiB. The resident GPU cache stayed at
3,000 entries. The 262,144 full-workload diagnostic preserved answer, all 47
token IDs, and residency, but the MTP-off/MTP-4 pair failed exact persistent
state parity in GDN, tail, pooled, pooled-full, and KV fields. Minimum
available RAM was 7.12 GiB, above the six-GiB floor, with no OOM kills. These
captures establish owner/path evidence, not a passing state result or proof
that context allocation alone caused the smaller pinned prefix.

Next hold expert ownership constant while comparing CPU and staged-GPU
expert-130 outputs from the same activation and model weights. Capture route
owners in paired state-repeatability controls and identify which allocations
reduce the pinned prefix at larger capacities. Do not attribute the observed
drift to NInfer arithmetic or change the kernel until those controls separate
tier assignment from context-capacity effects.

The 32K/65,536 measurements are in the local-only `32k-capacity-65536-*`
directories. Earlier 2K/16K controls and 262,144-capacity runs are in the
[prior screen](../2026-10-28-e6-q2-state-repeatability-length-screen/README.md)
and the ignored `fixed-capacity-262144/` directory. Owner captures are in
local-only `moe-owner-16k-cap*` directories. Raw captures, comparator JSON,
configs, logs, and supervisor samples remain local-only.

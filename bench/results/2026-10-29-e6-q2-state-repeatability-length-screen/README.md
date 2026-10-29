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

The single-expert result was checked with `native_expert_parity` on the same
Q2_0 model weights and the captured 2,560-float layer-2 activation. The
captured 32,768-capacity NInfer output was bitwise identical to the harness's
CUDA output; the 262,144-capacity CPU output was bitwise identical to its CPU
output. The cross-tier comparison was 1,825/2,560 outputs different, relative
L2 `1.064e-7`, max absolute `7.45e-9`; the independent CPU/GPU expert parity
test passed. This directly attributes the small layer-2 delta to the CPU/GPU
expert execution difference for this row. It does not explain the later state
divergence or exclude other capacity-sensitive causes.

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

The runtime allocation trace provides a direct capacity-linked memory cost.
With the same model, 16K prompt, 3,000-entry cache, and reserve, the device-0
`session` allocation was 991,516,160 bytes (0.92 GiB) at 32,768 capacity and
7,043,372,544 bytes (6.56 GiB) at 262,144, a 6.05 GiB increase. In
`session_bytes()`, QSA state and QSA buffers are sized from `max_context`;
other fixed session components remain in the same allocation. The paired
startup logs show the 6.00-to-4.0 GiB pinned-complement reduction alongside
this larger session. This is consistent with the larger context session using
Orin's shared physical DRAM and leaving less room to page-lock the expert
complement while preserving the 6 GiB headroom. Measure the intermediate
65,536 capacity before treating that relationship as a threshold or a sole
cause.

**16K/65,536 intermediate owner repeat:** a full 47-token MTP-off/MTP-4 pair
passed answer, token-ID, residency, and exact persistent-state comparisons.
At layer 2/position 16,383 the ten route IDs and all ten execution owners
matched the 32,768-capacity capture; expert 130 remained PCIe-staged GPU work.
The device-0 session allocation was 1,856,067,072 bytes (1.73 GiB), the
pinned expert complement remained 6.00 GiB, and startup shared RAM available
was 10.3–10.6 GiB. Minimum available RAM was 10.01 GiB and OOM kills were
zero. This intermediate capacity did not reproduce the owner switch or state
failure seen at 262,144. Pair runtime was 513.6 s; this instrumented correctness
run is not a performance benchmark.

**32K/65,536 third NInfer repeat with owner capture:** the fresh-process pair
matched the expected answer, all 47 token IDs, residency, and exact final state.
The all-layer GDN captures at positions 32,768, 32,790 and 32,813 were
bitwise identical between repeats (identical capture SHA-256). At model layer
2/position 32,768, both repeats routed IDs `230, 260, 75, 283, 42, 349, 22,
152, 506, 54` with the same owners: CPU for 230, 260, 283, 349 and 506;
PCIe-staged GPU for 75 and 152; resident GPU for 42, 22 and 54. The device-0
session was 1.73 GiB and pinned complement was 6.00 GiB. Pair wall time was
788.8 s, minimum available RAM 10.07 GiB, and OOM kills were zero. This
repeats NInfer's exact 32K/65,536 state result and owner plan; the earlier
Strata pair at this cell also passed state parity.

The 16K and 32K owner captures show that this high-capacity configuration
changes the tier of a different active expert at each prompt boundary. This
confirms capacity-sensitive owner assignment, while state causality remains a
separate question.

**32K/262,144 owner and MoE capture:** the 47-token MTP-off/MTP-4 pair
matched answer, tokens and residency but failed exact GDN, tail, pooled,
pooled-full and KV state parity. At model layer 2/position 32,768, both arms
routed the same IDs as the 65,536 pair, but expert 152 changed from
PCIe-staged GPU to CPU ownership. The device-0 session remained 7.04 GiB and
the pinned complement 4.11 GiB. Minimum available RAM was 6.91 GiB, above the
6 GiB floor, with zero OOM kills; pair runtime was 881.8 s.

The high-capacity MTP arms had bitwise-identical route IDs, MoE inputs, expert
parts and combined outputs at model layers 0–7, including the layer-2 CPU-owned
expert 152. However, captured GDN state first differed at GDN layer 2 at the
prompt boundary (relative L2 `3.49e-10`, max absolute `1.49e-8`); the first
changed GDN layer at the next two captured positions was layer 1. This grows
substantially in later state entries. Neither arm offered or accepted draft
tokens, so the mismatch is not explained by different speculative acceptance.
The single-expert `native_expert_parity` test passed on expert 152 and the same
captured activation; runtime CPU output matched the parity harness CPU output
bitwise, while CPU and CUDA outputs differed in 1,766/2,560 values (relative
L2 `9.72e-8`, max absolute `1.49e-8`). This supports the owner-path numeric
difference but does not explain the within-capacity GDN mismatch, since the
captured early MoE outputs were identical between arms. These are correctness
diagnostics; energy was not measured and the runtimes are not performance
qualification.

Next capture the 32K/65,536 MoE bundle at the same prompt boundary for direct
cross-capacity comparison of inputs and expert outputs. **That matched
comparison is now complete:** at model layer 1, routes, route weights, input,
and shared output were bitwise identical, but only experts 157 and 152 had
different outputs. For both experts, the 65,536-capacity NInfer outputs matched
the independent CUDA expert parity outputs bitwise, while the 262,144-capacity
runtime outputs matched the independent CPU outputs bitwise. CPU/GPU parity
differences exactly reproduced the cross-capacity deltas:

| Layer-1 expert | Changed outputs | Relative L2 | Max absolute |
| ---: | ---: | ---: | ---: |
| 157 | 1,873 / 2,560 | `1.201e-7` | `1.118e-8` |
| 152 | 1,916 / 2,560 | `1.123e-7` | `7.451e-9` |

At model layer 2, expert 152 again matched the CUDA output at 65,536 and the
CPU output at 262,144; it accounts for all 1,766 changed expert-part values
there (`9.724e-8` relative L2, max absolute `1.490e-8`). The MoE bundles show
the small owner-dependent differences accumulating: layer-2 input is already
different, and layer 7 reaches `2.58e-4` input relative L2 and `4.87e-3`
combined-output relative L2. This directly links the first cross-capacity MoE
drift to CPU-versus-GPU active-expert arithmetic for experts 157 and 152. It
does not explain the separate within-capacity GDN mismatch at 262,144.

**Matched owner-tier control with PCIe staging disabled:** set `--pcie-frac
0.0` at both 65,536 and 262,144 capacity, retaining the same 3,000-expert GPU
cache and running the full 32K retrieval fixture in fresh MTP-off/MTP-4
processes. Both capacity cells returned the exact answer, all 47 token IDs,
identical residency across MTP modes, and identical exact persistent state
between MTP modes. More strongly, the final state fingerprints were identical
across the two capacities as well. The 65,536 pair took 790.9 s and its
minimum available RAM was 10.06 GiB; the 262,144 pair took 877.5 s and minimum
available RAM was 6.98 GiB, 0.98 GiB above the required floor. Neither cell
recorded an OOM kill. Energy was not measured; clocks remained dynamic and
uncontrolled. These are correctness diagnostics, not performance benchmarks.

At model layer 2 / position 32,768, the two capacities routed the same ten
experts with the same owner classes: experts 230, 260, 75, 283, 349, 152 and
506 used CPU; 42, 22 and 54 used resident GPU. No active expert used the
PCIe-staged GPU tier. Comparing the MTP-off 8-layer bundles at the prompt
boundary showed bitwise identity for every captured field (route IDs/weights,
input, all ten expert outputs, shared output and combined output) at layers
0–7. The capacity-associated owner-tier differences and early MoE drift from
the staging-enabled runs therefore disappeared under this matched CPU/GPU
owner assignment. The previously observed 262,144 MTP state mismatch also
did not reproduce with staging disabled: both modes and both capacities had
the same state fingerprints. This strongly implicates the staging/owner-path
configuration in the earlier numeric and state differences; it does not
isolate whether the cause is CPU-versus-GPU expert arithmetic, transfer-time
data, or another interaction in the staged path. Do not infer that disabling
staging is a faster profile; performance was not measured here.

The MTP-off bundles from each PCIe-disabled cell also differ from their
staging-enabled counterpart beginning at layer 1, consistent with different
CPU versus staged-GPU active-expert arithmetic. Raw captures and comparator
JSON remain local-only under `pcie-disabled/`; they are excluded from Git.
Next investigate the staged path itself with same-capacity bundle and
accepted-state controls, preserving the exact answer/token/residency/state
gates. Keep the within-capacity mismatch as an issue specific to the staged
configuration until its trigger is localized.

**Same-capacity staged-path localization at 262,144:** comparing the staged
(`--pcie-frac 1.0`) and no-staging (`0.0`) MTP-off bundles at layer 1 / prompt
position 32,768 shows identical route IDs and weights, MoE input, and shared
output. Only active expert 86's output changes: 1,846/2,560 values, relative
L2 `1.0366e-7`, maximum absolute `7.45e-9`. An independent `native_expert_parity`
run used the exact captured activation and Q2_0 model weights. The staged
runtime output was bitwise identical to the CUDA parity output; the no-staging
runtime output was bitwise identical to the CPU parity output. The CPU/GPU
oracle difference exactly matched the runtime delta. Thus the first layer-1
MoE change follows the CPU-versus-CUDA active-expert arithmetic path. The
one-token owner-label capture did not emit a layer-1 record, so the specific
runtime owner label (for example, staged versus resident GPU) was not directly
captured for expert 86; the arithmetic path itself is independently confirmed.

At the same prompt boundary, committed GDN state first differs between the
staged and no-staging runs at GDN layer 1: 260,744/817,152 values, relative L2
`8.8824e-10`, maximum absolute `2.98e-8`. Two fresh no-staging runs were
bitwise identical across all 36 captured GDN layers. The high-capacity
no-staging MTP-off/MTP-4 pair also retained identical final state, whereas the
staging-enabled pair had failed that gate. This localizes the beginning of the
state trajectory divergence immediately after the first expert-part
difference, and strongly ties the earlier high-capacity state failure to
staging-dependent active-expert arithmetic. It does not establish whether
later divergence is caused only by this small first delta. Neither these
correctness captures nor their runtimes qualify a faster profile.

**Diagnostic execution notes:** the first repeat attempt was stopped after
process inspection showed the harness's staged-backend mode had overridden
the configured PCIe fraction back to `1.0`. Added `--staged-pcie-frac` to make
that override explicit and verifiable. A completed repeat at 65,536 with the
correct `0.0` value used an older local executable that did not contain the
current MoE-bundle diagnostic; it passed repeated answer/token/residency/state
checks and wrote owner traces, but the harness correctly reported the missing
requested bundle. It is not used for bundle conclusions. The completed paired
cells above use the diagnostic-capable `/tmp/strata-e6-boundary-build/strata`
and captured all requested MoE bundles. The preliminary raw files are retained
locally with the captures; none are included in Git.

The first expert-86 parity invocation failed because its requested dump
directory did not yet exist; it was rerun successfully after creating that
directory. The one-token owner-label capture at layer 1/position 32,768
returned no matching row and is not used as owner evidence. Raw command logs
and parity outputs remain local-only.

**16K/262,144 no-staging confirmation:** with the same `--pcie-frac 0.0`
control, the 16K retrieval pair also returned the exact answer, all 47 token
IDs, identical residency and exact final persistent state between MTP-off and
MTP-4. This reproduces the staging-disabled state recovery at a second prompt
length. Minimum available RAM was 7.36 GiB, 1.36 GiB above the reserve floor,
with zero OOM kills; pair runtime was 597.2 s. Comparing the staged and
no-staging committed state at the prompt boundary again found the first
difference at GDN layer 1 (298,674/817,152 values, relative L2 `8.2257e-10`,
maximum absolute `2.98e-8`). This confirms the layer-1 state divergence at
16K as well as 32K when the staged configuration is compared with the
CPU-fallback configuration. No energy or performance qualification was done.

The 32K/65,536 measurements are in the local-only `32k-capacity-65536-*`
directories. Earlier 2K/16K controls and 262,144-capacity runs are in the
[prior screen](../2026-10-28-e6-q2-state-repeatability-length-screen/README.md)
and the ignored `fixed-capacity-262144/` directory. Owner captures and the
32K/262,144 MoE bundle are in local-only `moe-owner-16k-cap*`,
`32k-capacity-65536-owner-repeat3/`, and `moe-bundle-32k-cap262144-ninfer/`
directories. Raw captures, comparator JSON, configs, logs, and supervisor
samples remain local-only.

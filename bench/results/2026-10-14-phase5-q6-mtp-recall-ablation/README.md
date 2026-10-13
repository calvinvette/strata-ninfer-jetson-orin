# MTP window and accepted-prefix retrieval ablation — Orin — 2026-10-13

This Phase 5 screen checks whether the accepted-only MTP4 path preserves a
held-out long-context task and persistent state relative to MTP-off. It used
the Qwen3.8 Flash-Next Coder IQ1_M artifacts, one 7,498-token planted-marker
prompt at 8K context, 48 requested output tokens, a 512-token warmup, FP16 KV,
3,000 requested expert-cache slots (3,903 actual), eight workers, Q6_K
warp-dequant, and `--adapt-accepted-only --adapt-every 4`. The six API runs
were fresh services in three randomized pairs; the direct state trace was a
separate correctness-only check.

| Pair | Order | MTP-off | MTP4 | Exact answers and recovery equal |
| ---: | --- | --- | --- | --- |
| 1 | MTP4, MTP-off | Pass | Pass | Yes |
| 2 | MTP4, MTP-off | Pass | Pass | Yes |
| 3 | MTP-off, MTP4 | Pass | Pass | Yes |

All six requests returned the three expected codes exactly once and in order,
then recovered on the same service with `RECOVERED`. Every arm produced the
same exact 41-token answer:

```text
EARLY=MAPLE-ORBIT-731, MIDDLE=COBALT-HARBOR-284, LATE=VELVET-COPPER-956
```

MTP4 offered/accepted 32/30 drafts in each API run. A separate direct trace
with `STRATA_ACCEPTED_PREFIX_TRACE` enabled matched all 41 output token IDs,
all nine final persistent main-state fingerprints, and all 14 shared
accepted-prefix checkpoints between MTP-off and MTP4. Shared committed-prefix
lengths were 1, 4, 8, 12, 15, 16, 20, 21, 24, 28, 32, 36, 40, and 41. The
traced MTP4 arm offered/accepted 34/30 drafts. Trace synchronization is
perturbative; this result is correctness evidence, not timing evidence.

The six supervised API runs used a 28-GiB cgroup ceiling and six-GiB host and
effective-availability floors. Minimum host availability was 13.20 GiB across
the runs; observed cgroup OOM count was zero. Clocks stayed under dynamic
policy, EMC frequency access was denied, and energy was not process-attributed.

Timing from three pairs is descriptive only. MTP4's median paired prompt-time
change was +0.79%; its median decode-time change was −15.74%. End-to-end paired
request changes were +1.04%, +0.63%, and −0.63%. This small correctness screen
does not satisfy a seven-pair performance confirmation, qualify a general
quality budget, or support a default change.

The first direct-trace wrapper attempt is retained in `state-trace/`. It
completed the MTP-off engine trace but exited before the MTP4 arm because its
parser counted nested accepted-prefix state hashes as separate final-state
records. The corrected parser filters the actual final-state line; the
successful retry in `state-trace-retry/` reused the completed MTP-off trace
and ran the MTP4 arm. This was a harness parsing failure, not an engine
failure. Phase 5 remains open for other prompts, formats, cache/resizing
conditions, and termination paths.

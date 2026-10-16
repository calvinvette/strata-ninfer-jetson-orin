# Coder CPU Q8_1 route × adaptive-swap screen — Orin — 2026-10-16

This one-block 2×2 screen tested whether the opt-in scalar CPU Q8_1 route
changes the known adaptive-residency state drift. All four arms used the same
Strata service binary, Coder IQ1_M artifact, accepted-only adaptation policy,
eight-swap cap, MTP-off profile and `512 → 2,048 → 512 → 512` prompt sequence.
The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. The candidate changes only
the CPU arithmetic for IQ2_S gate/up plus Q2_0 down experts.

| CPU expert arithmetic | Adapt cadence | Initial vs recovery tokens | Initial vs recovery state | Recovery vs continuation |
| --- | ---: | ---: | --- | ---: |
| Default GGML | 100,000 (delayed control) | 0/16 differ | exact | 0/16 differ |
| Default GGML | 4 | 0/16 differ | 5 fields differ | 16/16 differ |
| Q8_1 scalar candidate | 100,000 (delayed control) | 0/16 differ | exact | 0/16 differ |
| Q8_1 scalar candidate | 4 | 6/16 differ | 7 fields differ | 16/16 differ |

Both active-swap routes changed ownership in 34 of the first seven captured
expert rows; their earlier inputs and expert IDs matched. All 15 adaptive byte
and residency-table verifications passed in each active arm. The immediate
short recovery tokens in the Q8_1 active arm matched its delayed control, but
its state differed and the next same-prompt continuation differed at all 16
positions. The default active arm had the same continuation failure despite
matching its initial short tokens. Delayed adaptation reproduced initial
short-request tokens and state for both CPU routes. The Q8_1 candidate therefore
does not fix the observed state/continuation issue in this screen.

This is one randomized block, not the plan's three-block screen or seven-block
confirmation. It supplies no task-quality or performance claim: frequencies
were dynamic, elapsed times are single observations, and the route capture
covers layer 1 only. Across the four supervised arms, minimum host/admission
availability was 14.38 GiB, with zero cgroup memory events. EMC readback was
denied and energy was not request-attributed. Full token IDs, state fingerprints,
route captures, swap checks, one-second memory samples, clocks and service logs
are retained below; high-volume captures and logs are gzip-compressed.

Reproduce an arm on Orin1 from the repository root, substituting its cadence,
route flag and output path from `campaign.json`. For Q8_1 arms, add
`--cpu-q8-1-dot` before `--output`:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output <arm>/supervisor --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/run_cpu_q8_1_route.py \
  --adapt-every <100000-or-4> --adapt-swaps 8 --continuations 1 \
  --output <arm>/result
```

The Q8_1 CPU route remains opt-in. Adaptive residency migration remains
unqualified for this Coder workload; Phase 5 remains open.

The [direct FP32 GDN-state follow-up](gdn-state/README.md) captured numerical
state after the same short prompt. Cadence-4 swaps changed 4.6% relative L2
while preserving immediate output IDs; after a long request, active swaps
changed 73.8% relative L2 and all 16 output IDs, while delayed-swap recovery was
bit-identical to the initial short state. This quantifies the state difference
for one sequence without identifying its internal cause.

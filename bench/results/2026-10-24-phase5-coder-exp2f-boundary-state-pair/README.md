# Exp2f two-live state boundaries

## Result

The same-profile two-live exp2f replay retained exact outputs for both Coder
IQ1_M prompts: 120 tokens for slot 0 (natural end) and 128 for slot 1. Direct
accepted-prefix hashes nevertheless diverged. Slot 0 first differed at batch
position 75 / serial prefix 73, with 12 of 36 GDN allocation hashes changed.
Slot 1 first differed at batch position 89 / serial prefix 87, with 27 of 36
changed.

Direct committed-state captures at positions 75 and 89 refine those hash
boundaries. At position 75, slot 0 first differs at GDN model layer 32
(806,878/817,152 values, relative L2 0.003175); slot 1 is exact across all
captured layers. At position 89, slot 1 first differs at layer 12
(794,637/817,152 values, relative L2 `9.16e-5`). Thus the exp2f candidate's
exact output on this prompt pair still does not preserve all committed state.
These snapshots do not localize the upstream arithmetic that causes the
drift, establish a tolerance, or qualify the candidate/profile.

The run used the same 1,500-slot profile as the previous exp2f control/candidate
comparison (profile SHA-256 below; expert 233 at residency rank 12,287) and
enabled the exp2f CPU SwiGLU selector only for layer 9 / expert 233. Both
slots' output tokens matched their isolated serial controls. This is a direct
state-boundary follow-up on the same prompt pair, not held-out confirmation.
No serving default changed.

## Identity and resources

- Source commit: `62bb83b23aca6b94fdc28a6787a91c30bdb27198`.
- Candidate binary SHA-256: `ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`.
- Coder IQ1_M artifact revision: `5348543e0147355ac9cbcb031184a3546350988e`.
- Profile SHA-256: `1f03ed71cdac371e07480a3b4473e93be5cdfc9afb910f2fdac8491ac555502e`.
- The supervisor passed with minimum physical availability 17.73 GiB and zero
  sampled cgroup pressure/OOM events. GPU clocks varied from 306 to 1,300.5
  MHz; EMC readback was denied. Energy was not analyzed.

`summary.json` retains the paired metrics and identities. `direct-state-analysis.json`
and `hash-analysis.json` retain compact analyzer outputs. Raw state dumps,
engine logs and telemetry are local-only. The capture emitted roughly 900 MiB
of diagnostic state/log data; none of those raw captures is included in Git.

Reproduction used the existing `capture_position_state.py` harness with
`--positions 75,89 --layer all --serial-slot both --generated-tokens 128`, the
temporary expert profile above, `--exp2f-silu-layer 9 --exp2f-silu-expert
233`, and accepted-prefix plus batch-GDN hash tracing. Run under
`tools/integration/run_control.py` to retain the physical-memory guard.

Phase 5 remains open. This is correctness evidence for one prompt pair, not a
performance result or general multi-live state qualification.

# Two-live exp2f QSA state boundary

## Result

An opt-in QSA hash trace extended the same rank-12,287 expert-233 exp2f
two-live diagnostic. Both 32-token outputs were byte-for-byte equal to their
serial controls. The accepted-position QSA hashes nevertheless diverged:

- Slot 0 first differed at position 74 on token 264. QSA indexer and KV hashes
  changed in model layers 31, 35, 39, 43 and 47. Four earlier positions matched.
- Slot 1 first differed at position 88 on token 1149. QSA indexer and KV hashes
  changed in model layers 15, 19, 23, 27, 31, 35, 39, 43 and 47. Twenty earlier
  positions matched.

A direct GDN snapshot for slot 1 at position 89 found its first changed GDN
state at model layer 12. A separate same-profile layer-11 MoE capture at that
position matched the serial route, input activation, all ten expert parts and
combined output, despite several GPU→CPU owner changes. Earlier same-profile
captures also found exact layer-9 MoE and layer-10 GDN stage fields at position
89. Layer 11 is a QSA layer, so the GDN stage-dump interface cannot capture a
GDN stage there.

These traces place persistent-state differences in QSA as well as GDN while
outputs remain equal on this prompt pair. They do not identify a responsible
operation, show that the QSA and GDN observations share one cause, or establish
a tolerance. The QSA trace hashes state and copies KV data to host; it is
diagnostic only. No default or profile is qualified.

## Identity and resources

- Runtime source commit: `d93b48f0`.
- Candidate binary SHA-256: `ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`.
- Coder IQ1_M artifact revision: `5348543e0147355ac9cbcb031184a3546350988e`.
- Expert profile SHA-256: `1f03ed71cdac371e07480a3b4473e93be5cdfc9afb910f2fdac8491ac555502e`.
- The QSA-hash supervisor passed with 17.82 GiB minimum physical availability,
  zero sampled cgroup pressure/OOM events, and GPU clocks observed from 306 to
  1,300.5 MHz. EMC readback was denied. Energy was not analyzed.

`summary.json`, `qsa-analysis.json`, `direct-state-slot1.json` and `moe11.json`
retain compact comparisons. Large captures, logs and telemetry remain local.

The shared capture harness now exposes `--trace-batch-qsa-hashes` and a bounded
position range. `analyze_qsa_hashes.py` pairs those records with serial QSA
hashes by slot, token and exact hash alignment. The focused Python syntax check
and analysis completed successfully. Reproduction used the existing
`capture_position_state.py` harness with a 32-token allowance, position range
67–100, the profile and exp2f selector above, under
`tools/integration/run_control.py`.

Phase 5 remains open. This is correctness evidence from one prompt pair, not a
performance or general multi-live qualification.

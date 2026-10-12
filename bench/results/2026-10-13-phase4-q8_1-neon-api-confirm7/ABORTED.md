# Aborted preliminary API attempt

This directory preserves two non-qualifying starts while preparing the
Q8_1 NEON API comparison.

The first attempt wrapped `run_paired_controls.py` in `run_control.py`. Its
child supervisors then correctly refused the nested board lock before sending
any API workload. The terminal failure and outer supervisor record are retained
in `campaign/` and `outer-supervisor/`.

The second attempt started the IQ1_M native pack and completed one candidate
512/64 request, but was stopped before any baseline pair or full campaign. The
candidate's exact Q8_1 CPU path was not directly established for that mixed
expert-format model, so this isolated request is excluded from all comparisons.
Its partial output and termination are retained under `campaign-retry/`.

The controlled comparison instead uses the Q2_0 model and its Q2_0 pack, where
the native CPU Q2_0 route calls ARM `act_quant_any` and therefore dispatches to
the tested `act_quant_q8_1` implementation. See the separate
`2026-10-13-phase4-q8_1-neon-q2-api-confirm7` campaign.

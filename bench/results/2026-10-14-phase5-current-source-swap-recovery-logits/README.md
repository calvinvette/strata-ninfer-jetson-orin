# First-window logits after adaptive swaps — Orin — 2026-10-14

This extends the current-source cadence-4 short/long/short recovery diagnostic
with `STRATA_DUMP_FIRST_LOGITS`. The current native binary is
`e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`. Each of
the six raw files contains 248,320 float32 logits from the first verifier
window of its request: index `.0` is the first short request, `.1` is the long
request and `.2` is short recovery. The per-arm token/state comparisons and
the failed assertion are in `trace/results.json`; the supervisor's `status:
fail` is the expected strict recovery-equality failure, not a runtime or
memory failure.

The two MTP settings produced bit-identical first-window logits for each
corresponding request. Within each setting, however, the first short logits
and recovery short logits differed: relative L2 was 9.707%, maximum absolute
logit delta was 1.196, top-1 changed from token 27,775 to token 760, and 9 of
the top 10 tokens overlapped. Softmax KL at temperature 1 was 0.0130 from
first to recovery and 0.0141 in the reverse direction. These differences are
present before decoding starts. The calculation is reproducible with
`analyze_first_logits.py`; its output is retained in
`logit-analysis.json`.

Together with the same-binary delayed-swap control, this narrows the failure
to an adaptive-swap-history effect on the short prompt's first-window
computation, independent of MTP. It does not identify an individual swapped
expert, layer, or operator, and does not establish task-quality impact. No
serving setting or default changes.

The traced requests used the 512→2,048→512 incident sequence, 16 generated
tokens each, the IQ1_M artifact, 3,903 expert-cache slots, accepted-only
adaptation every four committed tokens, eight workers, and disabled CPU/GPU
prefill sharing. The 28-GiB supervisor retained 13.24 GiB minimum host and
admission availability, with zero sampled cgroup pressure/OOM events. Raw
logits, service logs, state traces and telemetry are retained under `trace/`
and `supervisor/`. `SHA256SUMS.txt` verifies the evidence.

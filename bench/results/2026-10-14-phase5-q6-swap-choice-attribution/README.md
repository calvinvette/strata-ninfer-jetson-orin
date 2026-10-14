# IQ1_M accepted-only adaptive-swap attribution — Orin — 2026-10-14

This supervised same-service reproduction extended the earlier 512 → 2,048 →
512-token sequence with `STRATA_TRACE_ADAPT=1`, which records the exact
layer/source/victim expert choices for each adaptive update. It used the
current candidate binary, IQ1_M model, 3,903 actual resident expert slots,
FP16 KV, accepted-only tracking, cadence 4, six generated tokens per prompt,
no CPU prefill share, and the existing incident prompt. MTP-off and MTP4 ran
in separate fresh services. The binary SHA256 is
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.

For each arm, four updates occurred during each request. The first two
requests selected 96 swaps at each update (384 choices per request); the final
short recovery selected 96, 79, 74 and 73 (322 choices). Both services
therefore logged 1,090 choices. Every corresponding `layer:incoming>victim`
choice batch was identical between MTP-off and MTP4, and each request's
transition set was disjoint from the other requests' sets. All three request
outputs and all nine persistent-state fields matched between MTP settings.

The first and final short outputs nevertheless differed in 14 of 16 token IDs
for both MTP settings (positions 0–11 and 14–15); seven persistent-state
fingerprints then differed, consistent with the changed token sequence. The
strict result assertion therefore returned 1 by design. The supervised process
completed normally; minimum host availability was 13.338 GiB and minimum
admission availability was 8.532 GiB, with zero sampled cgroup pressure/OOM
events. Raw traces, accepted-prefix records, outputs, memory samples and
tegrastats are retained under `trace/` and `supervisor/`.

Together with the earlier delayed-swap control, where `--adapt-every 100000`
restored first-versus-recovery output/state equality, this strengthens the
association with service-global cache residency changes. Matching choices
across MTP settings also show that this observed difference does not require
speculation. The evidence does not prove which numerical operation causes the
changed output, nor whether it harms task quality. Adaptive swaps remain
opt-in and unqualified for this repeated-request stability case; no runtime
default changed and Phase 5 remains open.

Run the analysis with:

```sh
python3 bench/results/2026-10-14-phase5-q6-swap-choice-attribution/analyze_swap_choices.py
```

The analyzer validates all 12 batches per arm, exact swap-choice equality
across MTP settings, request-level output/state parity, and the before/after
short-request differences. `SHA256SUMS.txt` covers the raw run, analysis,
helper script, report and candidate binary identity.

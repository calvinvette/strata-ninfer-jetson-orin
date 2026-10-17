# Coder GGUF Q2_0 vs IQ1_M comparison — Orin — 2026-10-17

This comparison tests `Q2_0` against `IQ1_M` from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned at
`5348543e0147355ac9cbcb031184a3546350988e`. The “Coder GGUF” used in the
2026-10-15 `phase7-current-source-coder-iq1m` results is IQ1_M; those results
were a single-quantization path check and did not compare Q2_0 with IQ1_M.
Artifact details and the tested service binary identity are in
[`model-source.txt`](model-source.txt) and [`model-sha256.txt`](model-sha256.txt).

The first three-pair same-CLI-argument screen is exploratory and confounded by
cache capacity: `--expert-cache 3000` occupied 3,955 MiB for Q2_0 and 7,615 MiB
for IQ1_M. Its results are retained in `screen3-per-arm/` and must not be read
as a quantization-only speed comparison. A calibrated IQ1_M argument of 1,558
produced the same 3,955 MiB cache footprint as Q2_0's argument of 3,000. A new
randomized three-pair cache-matched screen and a seven-pair held-out confirmation
then used fresh 28-GiB scopes for every arm.

An earlier campaign-wide wrapper attempt aborted before its third IQ1_M arm and
is excluded from all paired estimates; the complete same-argument screen was
rerun with a fresh scope for each arm. The incomplete attempt remains in
`screen3/` so the failed cell is retained.

Both campaigns used the same 8K context, FP16 KV, MTP disabled, prefill chunk
128, eight pool workers, prompt cache disabled, no adaptive swaps, 3,072 MiB
workspace reserve, tokenizer, and service binary. The screen used the 7,498-token
retrieval prompt; confirmation used a distinct 7,501-token retrieval prompt and
randomized pair order. Each request had to return three planted markers exactly
once and in order. All measured arms did so. This is one retrieval criterion,
not a broad model-quality comparison.

For the held-out seven-pair confirmation, the median IQ1_M paired change in
prompt processing time was **−30.83%** (20,000 paired-block bootstrap 95% interval
−31.12% to −30.43%). Median client total time changed **−31.55%** (interval
−31.81% to −31.15%). The first-visible streamed delta changed −30.95% (interval
−31.24% to −30.54%). The very short 36-token completions yielded noisy decode
throughput estimates (Q2_0 5.0–5.1 vs IQ1_M 12.4–12.5 tokens/s); prompt and total
latency are the more informative measures for this workload. No default/profile
is changed by this one task-specific comparison.

All 14 confirmation arms passed the independent marker and request checks. The
effective expert-cache footprint was exactly 3,955 MiB in every arm, although
resident slots differed (Q2_0 3,000; IQ1_M 2,008). Minimum host availability was
17.87 GiB, and minimum admission availability was 8.45 GiB; all observed
28-GiB cgroup memory-event counters were zero. Clocks were observed and dynamic;
no clocks were forced. No process-attributed energy measurement was collected.
The independent review is in [`confirm7-heldout-analysis.json`](confirm7-heldout-analysis.json);
raw per-arm request, memory, clock, engine, and supervisor data are retained
under `confirm7-heldout/`. The cache-matched screen and its analysis are in
`screen3-cache-matched/` and `screen3-cache-matched-analysis.json`.

Reproduce the independent review with:

```sh
python3 bench/results/2026-10-17-phase6-coder-quant-comparison/review_pairs.py \
  --root bench/results/2026-10-17-phase6-coder-quant-comparison/confirm7-heldout \
  --expected-prompt 7501 \
  --expected-codes COPPER-FERN-482 NORTH-EMBER-619 SILVER-OTTER-357 \
  --require-cache-match \
  --output /tmp/coder-quant-confirmation-review.json
```

This qualifies the tested retrieval behavior and comparative latency for the
specified Orin runtime, model revision, cache-byte budget and prompts. It does
not establish general answer quality, other context lengths, energy per token,
or a generally superior quantization. Phase 6 remains open for its other planned
interactions.

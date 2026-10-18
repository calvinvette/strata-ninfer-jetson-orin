# Q2_0 held-out cache × prefill confirmation — Orin — 2026-10-18

This seven-block randomized confirmation follows the exploratory cache ×
prefill screen in the sibling `2026-10-18-phase6-q2-cache-prefill-long-screen3`
result. It uses a newly generated near-limit retrieval prompt with distinct
marker values (7,506 formatted prompt tokens) so the confirmation task was not
used in screening. The four cells cross exact expert cache capacities of 3,000
and 3,500 slots with prefill chunks of 32 and 128. Every cell starts a fresh
service, uses a separate 512-token warmup, and makes one measured request under
`MemoryMax=28G` with the six-GiB headroom guard.

The model is Q2_0 with FP16 KV, MTP off, 8,192 context, eight workers, prompt
cache disabled and adaptive swaps disabled. Model files and supporting packs
remain under `~/models/strata-orin-validation`; the pinned model revision,
shard hashes, binary identity and configuration are in `artifacts.json`.

The seven-block campaign is currently running. This report will be updated with
exact-answer validation, per-cell results, paired block effects, bootstrap
intervals, physical-memory and clock summaries, and any failed or unsupported
cells after the campaign finishes. No default or profile decision is made
before that validation.

Reproduce on the Orin with a fresh output directory:

```sh
out=/tmp/q2-cache-prefill-confirm7
mkdir -p "$out"
cp bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/config.json "$out/"
cp bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/warmup-workload.json "$out/"
python3 bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/prepare_workload.py \
  --output "$out/workload-build" --context 8192
cp "$out/workload-build/workload-8192.json" "$out/workload.json"
bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/run_confirm7.sh "$out"
python3 bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/analyze_confirm7.py --root "$out"
```

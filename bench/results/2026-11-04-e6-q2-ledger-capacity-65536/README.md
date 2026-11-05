# 2K ledger backend screen at 64K context

Date: 2026-11-04. Hardware: Jetson AGX Orin, CUDA. Three randomized,
fresh-process pairs compared default Strata with strict NInfer on the same
Qwen3.8-Flash-Next Q2_0 weights, fixed 5,000-slot expert map, and exact
2,048-token signed-ledger task used in the 4K-, 8K-, 16K- and 32K-cap screens.
This run reserved a 65,536-token context. The only material within-pair change
was the expert backend.

## Result

All six warmups and six measured responses passed the independent exact JSON
oracle and produced the same 184-token answer. All three paired response
bodies matched, each arm recorded a 28.5% expert-cache hit rate, and the
supervised counters recorded zero accepted speculative drafts. The nominated
primary was decode throughput with a 5% useful-effect threshold. NInfer's
paired median decode change was **−0.27%** (displayed medians: Strata 5.98 and
NInfer 5.96 tok/s; three-pair screening interval −4.24% to +0.66%). The
interval crosses zero and the median is below the useful-effect threshold, so
no confirmation or profile promotion is indicated.

Prompt throughput changed −0.42% (95% interval −6.98% to −0.25%).
First-visible latency changed +0.41% (+0.25% to +7.51%) and client duration
+0.27% (+0.03% to +6.34%); positive latency changes are regressions. These
small three-pair effects do not show a useful NInfer gain.

Minimum available/admission memory was 7.82 GiB, 1.82 GiB above the required
floor. Sampled swap peaked at 2.68 GiB. The pre-existing cgroup OOM-kill
counter stayed at 1, with no increment. CPU and GPU clocks were dynamic and
uncontrolled (729.6–2,201.6 and 306–1,300.5 MHz); EMC readback was denied.
Rail samples were captured but energy was not integrated or used for
qualification. No persistent-state capture was run for this cell.

Separate 4K-, 8K-, 16K-, 32K- and 64K-cap screens are not jointly randomized
capacity/backend experiments. Their point estimates do not establish a
context-by-backend interaction or a reliable trend. This 64K-cap screen adds
no performance qualification.

## Reproduction and evidence

The tokenizer-verified [fixture](fixture.json), exact launch configurations
([Strata](strata-config.json), [strict NInfer](ninfer-config.json)),
[paired summary](summary.json) and machine-readable [evidence](evidence.json)
are retained here. Full process logs and telemetry remain outside Git under
`/tmp/e6-q2-ledger-capacity-65536/campaign/`.

```sh
python3 tools/integration/run_paired_controls.py \
  --baseline-config bench/results/2026-11-04-e6-q2-ledger-capacity-65536/strata-config.json \
  --candidate-config bench/results/2026-11-04-e6-q2-ledger-capacity-65536/ninfer-config.json \
  --workloads bench/results/2026-11-04-e6-q2-ledger-capacity-65536/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-65536-repro/campaign \
  --blocks 3 --seed 2026110465536 --timeout 1800 --no-trace --sample-clocks
```

Re-run the exact JSON oracle and summary in a fresh output directory:

```sh
mkdir -p /tmp/e6-q2-ledger-capacity-65536-repro/quality
for d in /tmp/e6-q2-ledger-capacity-65536-repro/campaign/block-*baseline \
         /tmp/e6-q2-ledger-capacity-65536-repro/campaign/block-*candidate; do
  python3 tools/integration/evaluate_e6_ledger_task.py "$d/requests.json" \
    > "/tmp/e6-q2-ledger-capacity-65536-repro/quality/$(basename "$d")-quality.json"
done
python3 tools/integration/summarize_e6_ledger_screen.py \
  --campaign /tmp/e6-q2-ledger-capacity-65536-repro/campaign \
  --quality-dir /tmp/e6-q2-ledger-capacity-65536-repro/quality \
  --fixture bench/results/2026-11-04-e6-q2-ledger-capacity-65536/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-65536-repro/summary.json
```

The API `model_name` label in the saved configs still says `cap16384`; the
health response and actual `--max-context 65536` argument confirm the context
used. This is one task, model and context-cap screen. It does not qualify
another model format or a native `.ninfer` artifact. E6 and E7 remain open.

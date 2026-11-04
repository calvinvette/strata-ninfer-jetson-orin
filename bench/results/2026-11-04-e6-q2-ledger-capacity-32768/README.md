# 2K ledger backend screen at 32K context

Date: 2026-11-04. Hardware: Jetson AGX Orin, CUDA. Three randomized,
fresh-process pairs compared default Strata with strict NInfer on the same
Qwen3.8-Flash-Next Q2_0 weights, fixed 5,000-slot expert map, and exact
2,048-token signed-ledger task used in the 4K-, 8K- and 16K-cap screens. This
run reserved a 32,768-token context. The only material within-pair change was
the expert backend.

## Result

All six warmups and six measured responses passed the independent exact JSON
oracle and produced the same 184-token answer. Each arm recorded a 28.5%
expert-cache hit rate, and all three paired response bodies matched. The
nominated primary was decode throughput with a 5% useful-effect threshold.
The paired median NInfer decode change was **−15.12%** (displayed medians:
Strata 6.11 and NInfer 5.26 tok/s; three-pair screening interval −37.35% to
+1.52%). The interval crosses zero and the median is a regression, so no
confirmation or profile promotion is indicated.

Prompt throughput changed −0.56% by paired median (interval −56.58% to
+2.79%). First-visible latency changed +0.44% (−2.70% to +129.93%) and client
duration +6.98% (−2.29% to +104.13%); positive latency changes are
regressions. The intervals are very wide because the first block's NInfer
measured request took 166.7 seconds at 3.83 tok/s, versus 81.7 seconds and
6.11 tok/s for its Strata pair. Its NInfer prefill rate was 17.27 tok/s and
TTFT 118.9 seconds; other NInfer TTFTs were 49.5–53.8 seconds. The slow pair
is retained without causal attribution.

Minimum available/admission memory was 8.47 GiB, 2.47 GiB above the required
floor. Sampled swap peaked at 1.41 GiB. The pre-existing cgroup OOM-kill
counter stayed at 1, with no increment. CPU and GPU clocks were dynamic and
uncontrolled (729.6–2,201.6 and 306–1,300.5 MHz); EMC readback was denied.
Rail samples were captured but energy was not integrated or used for
qualification. No persistent-state capture was run for this cell.

The separate 4K-, 8K-, 16K- and 32K-cap screens are not jointly randomized
capacity/backend experiments. Their point estimates do not establish a
context-by-backend interaction or a reliable trend. This 32K-cap screen adds
no performance qualification.

## Reproduction and evidence

The tokenizer-verified [fixture](fixture.json), exact launch configurations
([Strata](strata-config.json), [strict NInfer](ninfer-config.json)),
[paired summary](summary.json) and machine-readable [evidence](evidence.json)
are retained here. Full process logs and telemetry remain outside Git under
`/tmp/e6-q2-ledger-capacity-32768/campaign/`.

```sh
python3 tools/integration/run_paired_controls.py \
  --baseline-config bench/results/2026-11-04-e6-q2-ledger-capacity-32768/strata-config.json \
  --candidate-config bench/results/2026-11-04-e6-q2-ledger-capacity-32768/ninfer-config.json \
  --workloads bench/results/2026-11-04-e6-q2-ledger-capacity-32768/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-32768-repro/campaign \
  --blocks 3 --seed 2026110432768 --timeout 1800 --no-trace --sample-clocks
```

Run the exact JSON oracle on each process capture, then reproduce the summary:

```sh
mkdir -p /tmp/e6-q2-ledger-capacity-32768-repro/quality
for d in /tmp/e6-q2-ledger-capacity-32768-repro/campaign/block-*baseline \
         /tmp/e6-q2-ledger-capacity-32768-repro/campaign/block-*candidate; do
  python3 tools/integration/evaluate_e6_ledger_task.py "$d/requests.json" \
    > "/tmp/e6-q2-ledger-capacity-32768-repro/quality/$(basename "$d")-quality.json"
done
python3 tools/integration/summarize_e6_ledger_screen.py \
  --campaign /tmp/e6-q2-ledger-capacity-32768-repro/campaign \
  --quality-dir /tmp/e6-q2-ledger-capacity-32768-repro/quality \
  --fixture bench/results/2026-11-04-e6-q2-ledger-capacity-32768/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-32768-repro/summary.json
```

The API `model_name` label in the saved configs still says `cap16384`; the
health response and actual `--max-context 32768` argument confirm the context
used. This is one task, model and context-cap screen. It does not qualify
another model format or a native `.ninfer` artifact. E6 and E7 remain open.

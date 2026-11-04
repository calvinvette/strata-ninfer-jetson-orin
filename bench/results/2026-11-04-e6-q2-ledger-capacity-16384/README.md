# 2K ledger backend screen at 16K context

Date: 2026-11-04. Hardware: Jetson AGX Orin, CUDA. Three randomized,
fresh-process pairs compared default Strata with strict NInfer on the same
Qwen3.8-Flash-Next Q2_0 weights, fixed 5,000-slot expert map and exact
2,048-token signed-ledger task used in the 4K- and 8K-cap screens. This run
reserved a 16,384-token context. The only material within-pair change was the
expert backend.

## Result

All six warmups and six measured responses passed the independent exact JSON
oracle and returned the same 184-token result. Each arm recorded a 28.5%
expert-cache hit rate. The nominated primary was decode throughput with a 5%
useful-effect threshold. NInfer's paired median decode change was **+0.82%**
(Strata 6.52, NInfer 6.59 tok/s; three-pair screening interval −4.79% to
+1.00%). The interval includes zero and the median is below the useful-effect
threshold, so no confirmation or profile promotion is indicated.

Prompt throughput changed −1.99% (interval −22.84% to +3.04%). First-visible
latency changed +2.17% (−2.79% to +29.79%) and client duration changed +0.79%
(−2.02% to +19.54%); positive latency changes are regressions. These wide
intervals retain one slow final pair: its Strata/NInfer decode rates were
4.13/3.93 tok/s and client durations 108.7/130.0 seconds. The pair is not
excluded or attributed to a cause. All paired response texts and token counts
matched.

Minimum available/admission memory was 6.94 GiB, 0.94 GiB above the required
floor. Sampled swap peaked at 7.05 GiB in one NInfer process. The cgroup
OOM-kill counter was 1 before and after each process, with zero increment; it
was pre-existing. CPU and GPU clocks were dynamic and uncontrolled (729.6–2,201.6
and 306–1,300.5 MHz). EMC readback was denied. Rail samples were captured but
energy was not integrated or used for qualification.

Across separate 4K-, 8K- and 16K-cap screens of this fixed 2K task, the decode
medians were +1.71%, +1.22% and +0.82%, respectively. The 16K interval is wide
and includes zero. These screens were not jointly randomized across capacities;
they do not establish a context-by-backend interaction or a reliable trend.

## Reproduction and evidence

The tokenizer-verified [fixture](fixture.json), exact launch configurations
([Strata](strata-config.json), [strict NInfer](ninfer-config.json)),
[paired summary](summary.json) and machine-readable
[evidence](evidence.json) are retained here. Full process logs and telemetry
remain outside Git under `/tmp/e6-q2-ledger-capacity-16384/campaign/`.

```sh
python3 tools/integration/run_paired_controls.py \
  --baseline-config bench/results/2026-11-04-e6-q2-ledger-capacity-16384/strata-config.json \
  --candidate-config bench/results/2026-11-04-e6-q2-ledger-capacity-16384/ninfer-config.json \
  --workloads bench/results/2026-11-04-e6-q2-ledger-capacity-16384/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-16384/campaign \
  --blocks 3 --seed 2026110416384 --timeout 1800 --no-trace --sample-clocks
```

Run the exact JSON oracle on each process capture, then reproduce the summary:

```sh
for d in /tmp/e6-q2-ledger-capacity-16384/campaign/block-*baseline \
         /tmp/e6-q2-ledger-capacity-16384/campaign/block-*candidate; do
  python3 tools/integration/evaluate_e6_ledger_task.py "$d/requests.json" \
    > "/tmp/e6-q2-ledger-capacity-16384/$(basename "$d")-quality.json"
done
python3 tools/integration/summarize_e6_ledger_screen.py \
  --campaign /tmp/e6-q2-ledger-capacity-16384/campaign \
  --quality-dir /tmp/e6-q2-ledger-capacity-16384 \
  --fixture bench/results/2026-11-04-e6-q2-ledger-capacity-16384/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-16384/summary.json
```

This is one task, model and context-cap screen. It does not qualify another
model format or a native `.ninfer` artifact. E6 and E7 remain open.

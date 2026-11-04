# 2K ledger backend screen at 4K context

Date: 2026-11-04. Hardware: Jetson AGX Orin, CUDA. Three randomized,
fresh-process pairs compared default Strata with strict NInfer on the same
Qwen3.8-Flash-Next Q2_0 weights, fixed 5,000-slot expert map and exact
2,048-token signed-ledger task used by the separate 8K-cap screen. This run
reserved a 4,096-token context. The only material within-pair change was the
expert backend.

## Result

All six warmups and six measured responses passed the independent exact JSON
oracle and returned the same 184-token result. Each arm recorded a 28.5%
expert-cache hit rate. The nominated primary was decode throughput with a 5%
useful-effect threshold. NInfer's paired median decode change was **+1.71%**
(Strata 6.65, NInfer 6.77 tok/s; three-pair screening interval +1.09% to
+2.94%). The interval is above zero, but the effect remains below the useful
threshold, so no confirmation or profile promotion is indicated.

Prompt throughput changed +1.42% (interval −5.94% to +3.29%). First-visible
latency changed −1.33% (−3.05% to +6.48%) and client duration changed −1.26%
(−2.99% to +3.23%); negative latency changes favor NInfer. These intervals
are coarse and cross zero. The exact answer and all prompt/output counts
matched within every pair.

Minimum available/admission memory was 9.30 GiB; sampled swap peaked at
2.38 GiB. The cgroup OOM-kill counter was 1 before and after each process,
with zero increment; this is a pre-existing counter, not a new OOM event. CPU
and GPU clocks were dynamic and uncontrolled (729.6–2,201.6 and 306–1,300.5
MHz). EMC readback was denied. Rail samples were captured but energy was not
integrated or used for qualification.

The same task at an 8K configured context cap measured +1.22% decode change
(95% three-pair screen interval +0.33% to +3.05%). Both cap-specific screens
show a small positive NInfer decode effect below the 5% gate. They were run as
separate screens, so their difference does not establish a context-by-backend
interaction or a general NInfer gain.

## Reproduction and evidence

The tokenizer-verified [fixture](fixture.json), exact launch configurations
([Strata](strata-config.json), [strict NInfer](ninfer-config.json)),
[paired summary](summary.json) and machine-readable
[evidence](evidence.json) are retained here. Full process logs and telemetry
remain outside Git under `/tmp/e6-q2-ledger-capacity-4096/campaign/`.

```sh
python3 tools/integration/run_paired_controls.py \
  --baseline-config bench/results/2026-11-04-e6-q2-ledger-capacity-4096/strata-config.json \
  --candidate-config bench/results/2026-11-04-e6-q2-ledger-capacity-4096/ninfer-config.json \
  --workloads bench/results/2026-11-04-e6-q2-ledger-capacity-4096/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-4096/campaign \
  --blocks 3 --seed 202611044096 --timeout 1800 --no-trace --sample-clocks
```

Run the exact JSON oracle on each process capture, then reproduce the summary:

```sh
for d in /tmp/e6-q2-ledger-capacity-4096/campaign/block-*baseline \
         /tmp/e6-q2-ledger-capacity-4096/campaign/block-*candidate; do
  python3 tools/integration/evaluate_e6_ledger_task.py "$d/requests.json" \
    > "/tmp/e6-q2-ledger-capacity-4096/$(basename "$d")-quality.json"
done
python3 tools/integration/summarize_e6_ledger_screen.py \
  --campaign /tmp/e6-q2-ledger-capacity-4096/campaign \
  --quality-dir /tmp/e6-q2-ledger-capacity-4096 \
  --fixture bench/results/2026-11-04-e6-q2-ledger-capacity-4096/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-4096/summary.json
```

This is one task, model and context-cap screen. It does not qualify another
model format or a native `.ninfer` artifact. E6 and E7 remain open.

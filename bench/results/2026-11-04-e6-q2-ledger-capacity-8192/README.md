# 2K ledger 8K-capacity replication

Date: 2026-11-04. Hardware: Jetson AGX Orin, CUDA. Three randomized,
fresh-process pairs compared default Strata with strict NInfer on the same
Qwen3.8-Flash-Next Q2_0 model weights, fixed 5,000-slot expert map and exact
2,048-token signed-ledger task. The configured context cap was 8,192 tokens.
The backend was the only material difference within each pair.

## Result

All six warmup and six measured responses passed the independent exact JSON
oracle. Every measured response returned the same correct 184-token answer;
both backends recorded a 28.5% expert-cache hit rate. The nominated primary
was decode throughput with a 5% useful-effect threshold. The paired median
NInfer decode effect was **−1.15%** (Strata 6.54, NInfer 6.48 tok/s; three-pair
screening interval −22.27% to −0.32%). The interval reflects a slow NInfer arm
in block 0, which is retained in the result. The other two pairs were nearly
tied. This screen found no useful decode gain and does not justify a seven-pair
confirmation or profile promotion.

| Measure | Paired median NInfer change | Three-pair screening interval |
| --- | ---: | ---: |
| Prompt throughput | −1.90% | −17.67% to +1.17% |
| Decode throughput | −1.15% | −22.27% to −0.32% |
| First-visible latency | +1.95% | −1.19% to +21.44% |
| Client duration | +1.64% | −0.58% to +24.13% |

Positive latency changes are slower. The small sample and one large slow arm
make the interval coarse; this is a screening result, not a general estimate.
The exact outputs and 28.5% hit rates match across pairs, but the decode-rate
variation remains unexplained. Clocks were observed, not controlled.

Minimum available/admission memory was 9.19 GiB, above the 6 GiB headroom
floor. Sampled swap peaked at 2.06 GiB. The maximum observed OOM-kill counter
was 1, with no increment during the run. CPU clocks ranged from 729.6 to
2,201.6 MHz and GPU clocks from 306 to 1,300.5 MHz. EMC readback was denied.
Instantaneous rail samples were captured but energy was not integrated or
used for qualification.

## Same-day six-pair view of the 8K-cap cell

An earlier independent three-pair screen of this exact task and 8K cap
measured +1.22% median decode TPS change (three-pair interval +0.33% to
+3.05%). Pooling its six pairs with this same-day replication gives a
**+0.00%** median decode effect (95% six-pair paired-bootstrap interval
−11.71% to +2.14%). The pooled median prompt-throughput change was −1.17%
(−11.16% to +1.45%), first-visible latency +1.22% (−1.42% to +13.08%) and
client duration +0.89% (−1.39% to +13.30%). The intervals are wide and include
small regressions and gains; no useful backend effect is established. The
slow NInfer arm from the replication remains in the pool. This exploratory
six-pair pooling is not a preregistered seven-pair confirmation.

The [initial 8K-cap screen](../2026-11-04-e6-q2-ledger-aggregation-screen/README.md)
and this replication use the same task, Q2_0 weights, fixed map, runtime
binary and configured cap. The 4K, 16K, 32K and 64K cap results remain separate
cells and do not establish a context-cap interaction. Neither screen
qualifies another model, codec or native `.ninfer` artifact. E6 and E7 remain
open.

## Reproduction and evidence

The tokenizer-verified [fixture](fixture.json), launch configurations
([Strata](strata-config.json), [strict NInfer](ninfer-config.json)), full
[paired summary](summary.json), [six-pair pooled summary](same-day-pooled-summary.json)
and [machine-readable evidence](evidence.json)
are retained here. Full process logs and telemetry remain outside Git under
`/tmp/e6-q2-ledger-capacity-8192/campaign/`.

```sh
python3 tools/integration/run_paired_controls.py \
  --baseline-config bench/results/2026-11-04-e6-q2-ledger-capacity-8192/strata-config.json \
  --candidate-config bench/results/2026-11-04-e6-q2-ledger-capacity-8192/ninfer-config.json \
  --workloads bench/results/2026-11-04-e6-q2-ledger-capacity-8192/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-8192/campaign \
  --blocks 3 --seed 202611048192 --timeout 1800 --no-trace --sample-clocks
```

Recreate the same-day pooled six-pair summary from the tracked evidence:

```sh
python3 tools/integration/combine_e6_ledger_screens.py \
  --screen bench/results/2026-11-04-e6-q2-ledger-aggregation-screen/summary.json \
          bench/results/2026-11-04-e6-q2-ledger-aggregation-screen/evidence.json \
  --screen bench/results/2026-11-04-e6-q2-ledger-capacity-8192/summary.json \
          bench/results/2026-11-04-e6-q2-ledger-capacity-8192/evidence.json \
  --output bench/results/2026-11-04-e6-q2-ledger-capacity-8192/same-day-pooled-summary.json
```

The quality oracle and paired summary used (create the output directory first):

```sh
for d in /tmp/e6-q2-ledger-capacity-8192/campaign/block-*baseline \
         /tmp/e6-q2-ledger-capacity-8192/campaign/block-*candidate; do
  python3 tools/integration/evaluate_e6_ledger_task.py "$d/requests.json" \
    > "/tmp/e6-q2-ledger-capacity-8192/quality/$(basename "$d")-quality.json"
done
python3 tools/integration/summarize_e6_ledger_screen.py \
  --campaign /tmp/e6-q2-ledger-capacity-8192/campaign \
  --quality-dir /tmp/e6-q2-ledger-capacity-8192/quality \
  --fixture bench/results/2026-11-04-e6-q2-ledger-capacity-8192/fixture.json \
  --output /tmp/e6-q2-ledger-capacity-8192/summary.json
```

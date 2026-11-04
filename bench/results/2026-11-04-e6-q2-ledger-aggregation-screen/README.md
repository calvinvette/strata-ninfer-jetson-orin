# Held-out ledger aggregation screen

Date: 2026-11-04. Hardware: Jetson AGX Orin. Model: Qwen3.8-Flash-Next
Q2_0. Three randomized fresh-process pairs compared default Strata with strict
NInfer using the same learned 5,000-slot resident-expert map.

## Result

The 2,048-token prompt contains a small signed ledger and requests a JSON
summary by region: record count, signed sum, maximum record ID/value, plus
overall count and sum. The independent oracle checks the exact structure and
values. All six measured outputs and six warmups passed; each response returned
the same correct 184-token JSON. This adds structured data aggregation as a
third quality task family alongside retrieval/arithmetic and code generation.

The nominated primary was decode throughput, with a 5% useful-effect gate.
NInfer's median paired effect was +1.22% (Strata 6.56, NInfer 6.58 tok/s), with
a 95% three-pair screening interval of +0.33% to +3.05%. It remained below the
useful-effect threshold, so no confirmation was indicated. Prompt throughput
changed −0.43% (95% interval −4.65% to +1.73%); first-visible latency changed
+0.48% (−1.65% to +4.72%); client duration changed +0.15% (−2.21% to +2.48%).
Positive latency changes are regressions. The other intervals cross zero and
are coarse with three pairs. No useful same-map NInfer request-level gain was
demonstrated.

Both backends recorded a 28.5% expert-cache hit rate and identical API
responses in all three pairs. No speculative drafts were accepted. Minimum
available and admission memory was 9.13 GiB; sampled swap peaked at 2.50 GiB
and cgroup OOM-kill counters remained zero. CPU frequencies ranged from
729.6–2,201.6 MHz and GPU frequencies from 306–1,300.5 MHz; clocks were
observed, not controlled. EMC readback was denied. Instantaneous named-rail
samples were captured by tegrastats but were not integrated or used for
qualification; no energy result is claimed.

## Reproduction and limits

The [fixture](fixture.json) is tokenizer-verified at exactly 2,048 formatted
tokens. The [evidence](evidence.json) records model and executable hashes,
the fixed map, per-pair metrics, output identity, resource observations and
the paired bootstrap intervals. Raw supervised captures remain outside Git at
`/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-ledger-aggregation-20261104/`.

The task generator and quality oracle can be checked with:

```sh
python3 tools/integration/make_e6_ledger_workload.py \
  --tokenizer /path/to/strata-orin-validation/pack/tokenizer \
  --output /tmp/ledger-workload.json --prompt-tokens 2048 --generate-tokens 256
PYTHONPATH=tools/integration python3 tools/integration/test_evaluate_e6_ledger_task.py
PYTHONPATH=tools/integration python3 tools/integration/test_summarize_e6_ledger_screen.py
PYTHONPATH=tools/integration python3 tools/integration/test_compare_e6_ledger_state.py
```

## Accepted-prefix state check

A separate instrumented Strata/NInfer pair ran the same fixture with one
warmup and one measured request per backend. Both warmups and measured answers
passed the oracle and returned the same 184-token JSON. At every one of the 184
measured accepted-prefix commits, token IDs and all recorded state fingerprints
matched exactly across backends: `L`, GDN, PLE, tail, dead, pooled,
pooled-full, KV, MTP, stale and PLE previous-token state. The canonical trace
SHA-256 is `81349991a2e9039d506f6aff530ef050c19e8864ea3671cb43472fd016048d9e`.
Minimum available memory was 9.27 GiB for each arm, sampled swap peaked at
2.26 GiB for Strata and 2.21 GiB for NInfer, and sampled OOM-kill counters were
zero. The raw traces are outside Git in the `statecheck/` subdirectory of the
campaign path. Trace hashing slowed decode to about 1 tok/s, so these timings
are excluded; this establishes state parity only for this task, model, map and
request shape.

The compact machine-readable comparison is in
[`statecheck-summary.json`](statecheck-summary.json). Recreate it from the
external raw capture with:

```sh
python3 tools/integration/compare_e6_ledger_state.py \
  --strata-log /tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-ledger-aggregation-20261104/statecheck/strata/engine.log \
  --ninfer-log /tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-ledger-aggregation-20261104/statecheck/ninfer/engine.log \
  --strata-requests /tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-ledger-aggregation-20261104/statecheck/strata/requests.json \
  --ninfer-requests /tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-ledger-aggregation-20261104/statecheck/ninfer/requests.json \
  --output bench/results/2026-11-04-e6-q2-ledger-aggregation-screen/statecheck-summary.json
```

Two setup attempts are retained in the raw directory and excluded from the
screen: a 128-token cap truncated the otherwise valid JSON, and a later run
omitted `allow_natural_stop`, causing the harness to reject the correct
184-token natural EOS. The final campaign allows natural EOS and uses a
256-token ceiling. This is one synthetic 2K task on one Q2_0 model; it adds
quality coverage but does not qualify general reasoning, long-context state,
or NInfer performance. E6 and E7 remain open.

# Held-out code-generation backend screen

Date: 2026-11-04. Hardware: Jetson AGX Orin, CUDA. Model: Qwen3.8-Flash-Next
Q2_0. Three randomized, fresh-process pairs compare the default Strata expert
backend with strict NInfer at the same fixed 5,000-slot learned map.

## Result

All six measured responses and six warmups returned the same Python function.
An independent evaluator ran five executable interval-merging cases, including
overlap, adjacency, unsorted inputs, negative values, empty input and a check
that the input list remains unchanged. All twelve outputs passed. The model's
generated code hash was identical in all arms.

The nominated primary was decode throughput, with a 5% useful-effect gate.
NInfer's paired median was +1.0% (Strata 5.33, NInfer 5.33 tok/s); the 95%
three-pair screening interval was −5.9% to +9.6%. It did not meet the effect
threshold and the interval includes zero. Prompt throughput changed +2.8%
(27.58 to 28.35 tok/s; interval +1.3% to +159.0%). First-visible latency
changed −2.7% (74.52 to 72.50 s; interval −61.3% to −1.3%), and client time
changed −1.2% (94.39 to 93.62 s; interval −56.0% to −0.8%). The intervals are
coarse with three pairs. One Strata arm had unusually slow prefill and TTFT;
it is retained without causal attribution. No metric meets the 5% decode gate,
so no confirmation is indicated and no NInfer acceleration is claimed.

Both backends had the same 19.9% expert-cache hit rate. The 5K map was held
fixed from the retrieval campaign, so this is a backend comparison on a
held-out task with relatively low resident-route coverage. The result does not
measure a code-task-specific map benefit.

## Controls and limits

Both arms used the same Q2_0 files, 2,048-token exact-length prompt, 128-token
output limit, map, 5,000 GPU slots, 6 GiB RAM expert budget, 8,192 context,
prefill 128, MTP-2, eight workers, prompt cache off, adaptation off and no
PCIe staging. The Strata arm used the default backend; strict NInfer added
`--expert-backend ninfer --expert-backend-strict`. API model-name labels differed
by backend, but model files and runtime controls were identical; the report
does not treat those labels as different model artifacts.

The evidence records SHA-256 for both model shards. The second Q2_0 shard has
the same size and digest as the local IQ1_M second shard, while the first-shard
digest differs; retain the complete two-shard identity when reproducing this
result instead of identifying the quantization from shard two alone.

Minimum available memory was 9.13 GiB, peak sampled swap was 0.95 GiB, and
sampled cgroup OOM kills were zero. CPU and GPU clocks were observed dynamically
(729.6–2,201.6 MHz CPU; 306–1,300.5 MHz GPU) and not controlled. EMC readback
was denied; energy was not measured. The three-pair intervals are screening
estimates, not confirmation. This one code-generation task broadens E6 quality
coverage but does not resolve the lack of a useful NInfer backend effect,
long-prompt state differences or the broader task/model requirements.

The [combined task/context chart](../../2026-10-31-e6-q2-fixed-map-ORBIT-screen/same-map-backend-screens.svg)
shows this code-task cell alongside the separate 2K retrieval cell and the
retrieval screens through 240K. Points and intervals remain per-task screens;
they are not pooled.

## Accepted-prefix state check

A separate instrumented pair ran the same code task in fresh Strata and strict
NInfer processes, each with a warmup and measured request. Both requests in
both processes passed the executable oracle and returned the same 107-token
code. All committed token IDs and recorded GDN, PLE, QSA tail, pooled, KV,
MTP, stale, dead, pooled-full and PLE previous-token fingerprints matched at
all 107 accepted prefixes across backends and request ordinals. Minimum
available memory was 9.14 GiB for Strata and 9.17 GiB for NInfer; both reported
19.9% expert hits. Hashing and accepted-prefix tracing invalidate timing
interpretation, so those rates are excluded. This closes state parity only for
this fixed-map code task and does not resolve long-prompt state differences.
Full traces remain outside Git under the `statecheck/` directory of the raw
capture path; the canonical trace hash is in [`evidence.json`](evidence.json).

Reproduce the oracle with:

```sh
python3 tools/integration/test_evaluate_e6_code_task.py
python3 tools/integration/evaluate_e6_code_task.py <requests.json>
```

The paired campaign used this invocation (the generated configs and fixture
are retained under the raw-capture directory):

```sh
python3 tools/integration/run_paired_controls.py \
  --baseline-config /tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-code-generation-20261104/strata.json \
  --candidate-config /tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-code-generation-20261104/ninfer.json \
  --workloads /tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-code-generation-20261104/workloads.json \
  --output /tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-code-generation-20261104/screen \
  --blocks 3 --seed 20261104 --timeout 1800 --no-trace --sample-clocks
```

The compact pair data, configuration hashes, memory and clock observations,
and exact result identity are in [`evidence.json`](evidence.json). Raw campaign
captures remain outside Git at `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-code-generation-20261104/`.

# 8K code-generation backend screen

Date: 2026-11-04. Hardware: Jetson AGX Orin, CUDA. Three randomized,
fresh-process pairs compared Strata's default expert backend with strict NInfer
on the Qwen3.8-Flash-Next Q2_0 model. Both used the same learned 5,000-slot
resident map, 6 GiB RAM expert complement, eight workers, prefill chunk 128,
configured speculation 2 (zero drafts accepted), no prompt cache, no adaptation,
and no PCIe staging. The configured context was 16,384 tokens to fit the exact
8,192-token input plus generation.

## Results

All six warmups and six measured requests passed the API checks and an
independent executable oracle for interval merging. Each returned the same
107-token Python function; all generated code had SHA-256
`5df0a140c98a2222561b219450c8298cd4bc023bdeea65e815626cded949cc58`.
Expert-cache hit rate was 20.0% in every arm. The prompt used 8,089 repetitions
of `red` before the task to construct an exactly 8,192-token formatted request.
This is a filler-extended long-input code task, not a natural 8K document or
codebase prompt.

Decode throughput was the registered primary. Median paired NInfer change was
**+0.14%** (Strata 5.35, NInfer 5.37 tok/s; 95% three-pair screening interval
−0.16% to +3.75%), below the 5% useful-effect threshold. Prompt throughput
changed +0.59% (interval −1.40% to +1.75%), client first-visible latency
changed −0.58% (−1.73% to +1.65%), and client duration changed −0.47%
(−2.02% to +1.17%). None supports a useful backend advantage. Do not run
confirmation or promote a profile from this screen.

Minimum available/admission memory was 8.97 GiB, above the 6 GiB floor, with
zero sampled OOM kills. Maximum sampled swap was 4.44 GiB in one NInfer arm;
other arms peaked between 1.14 and 1.47 GiB. CPU/GPU clocks were dynamic and
uncontrolled (729.6–2,201.6 / 306–1,300.5 MHz). EMC readback was denied and
energy was not measured. This resource variability and three-pair sample limit
the performance interpretation. No 8K accepted-prefix state capture was run;
state parity evidence remains limited to the separate 2K code and ledger tasks.

## Reproduction

The exact workload, launch configurations, compact pair summary and source,
model, map and binary identities are retained in this directory. Raw process
captures remain outside Git at the path in `evidence.json`.

```sh
python3 tools/integration/run_paired_controls.py \
  --baseline-config bench/results/2026-11-04-e6-q2-code-generation-8k-screen/strata-config.json \
  --candidate-config bench/results/2026-11-04-e6-q2-code-generation-8k-screen/ninfer-config.json \
  --workloads bench/results/2026-11-04-e6-q2-code-generation-8k-screen/fixture.json \
  --output /tmp/e6-code-8k-repeat --blocks 3 --seed 202611048192 \
  --timeout 3600 --no-trace --sample-clocks
```

Run the quality oracle and validate/summarize the captured campaign:

```sh
python3 tools/integration/evaluate_e6_code_task.py /tmp/e6-code-8k-repeat/block-0-baseline/requests.json
python3 tools/integration/summarize_e6_code_screen.py \
  --campaign /tmp/e6-code-8k-repeat \
  --fixture bench/results/2026-11-04-e6-q2-code-generation-8k-screen/fixture.json \
  --output /tmp/e6-code-8k-repeat-summary.json
```

The combined same-map screen chart includes this as a separate 8K code-task
point from the retrieval workload.

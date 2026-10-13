# Q6 cache × context screen

This randomized three-block screen tested the interaction between requested
expert-cache capacity and context reservation on the Orin IQ1_M Q6 warp-dequant,
accepted-only MTP4 path. It is a resource and throughput screen, not a numerical
quality qualification or a serving-profile promotion.

The run used Strata build `857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`
with the local IQ1_M Coder pack and PLE shard under
`/home/calvin/models/strata-orin-validation/`. Their SHA-256 checksums are
`e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` (base
shard) and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`
(PLE shard). Each fresh server used FP16 KV,
prefill 64, 8 workers, MTP4, accepted-only adaptive swaps every four tokens,
Q6_K warp dequant, prompt cache disabled and no `STRATA_TRACE`. The prepared
512-token prompt asked for a 200-word processor explanation; each request was
capped at 64 generated tokens, so it deliberately measured a fixed load and did
not complete that task's quality rubric.

The factors were `--expert-cache` arguments of 3,000 or 5,000 and maximum
context of 8,192 or 16,384 tokens. Strata interprets this argument as a budget
in units of the largest expert blob; it is not a literal slot count. The
runtime's capability report gives the actual resident slots, which can vary
with context and startup allocation. Three randomized complete blocks used
seeds 202610141–202610143. Each cell ran in a fresh service with one warmup and
three measured requests. The outer user systemd scope was limited to 28 GiB;
`run_control.py` separately enforced the 6 GiB available-host floor and recorded
cgroup and OS memory telemetry. The optional `--no-trace` switch was added to
`cache_context_screen.py` so request timing did not carry state-trace overhead;
trace remains enabled by default for existing invocations.

All 12 cells and 36 measured requests passed, with exactly 512 prompt tokens,
64 generated tokens and zero prompt-cache tokens. No cgroup OOM or OOM-kill
events were observed. Minimum available host memory by randomized block was
8.22, 8.27 and 8.23 GiB, respectively, above the six-GiB floor. The full
per-cell minima, request logs, capability reports, commands and supervisor
records are retained beside this report.

| `--expert-cache` argument | Context | Actual slots across blocks | Median prompt tok/s by block | Median decode tok/s by block | Minimum available RAM by block |
| ---: | ---: | --- | --- | --- | --- |
| 3,000 | 8K | 3,903 / 3,903 / 3,903 | 35.9 / 36.2 / 36.0 | 18.3 / 17.7 / 17.5 | 13.26 / 13.02 / 13.04 GiB |
| 3,000 | 16K | 3,903 / 3,903 / 3,903 | 35.8 / 35.8 / 35.8 | 16.0 / 18.4 / 18.7 | 12.81 / 13.05 / 13.08 GiB |
| 5,000 | 8K | 6,519 / 6,519 / 4,600 | 46.1 / 46.3 / 38.4 | 20.1 / 20.2 / 19.7 | 8.22 / 8.36 / 12.07 GiB |
| 5,000 | 16K | 5,851 / 6,519 / 6,519 | 41.5 / 45.4 / 46.6 | 19.8 / 20.2 / 20.1 | 9.42 / 8.27 / 8.23 GiB |

The per-cell `campaign.json` retains the historical field name
`requested_cache_lower_bound`; it stores this exact `--expert-cache` argument
and does not mean the engine promised that many slots.

These are medians of three requests within each process; the three block values,
not the requests, are the independent repetitions. The 5,000 budget argument
did not produce a fixed allocation: actual capability reports ranged from 4,600 to
6,519 slots. Prompt throughput cache effects ranged from +6.7% to +30.2% at 8K
and +15.9% to +26.8% at 16K across paired blocks. Decode cache effects ranged
from +9.8% to +14.1% at 8K and +7.5% to +23.8% at 16K. The direction was
positive in this small screen, but the size varied and this workload did not
pass an output-quality rubric. Context effects and the cache × context
difference-in-differences also varied by block; no fitted response model is
justified by three blocks. These numbers nominate a held-out confirmation; they
do not establish a performance or capacity recommendation.

Outputs were not byte-identical across all requests. In each cell using the
`--expert-cache 3000` setting,
the second measured response had a different prose digest than the first and
third in all three blocks. The `--expert-cache 5000` cells were mostly stable, with one
additional distinct digest in the first 5,000/16K cell. Because the 64-token
cap cannot satisfy the workload's requested 200-word rubric, this was not
classified as a quality pass or failure. It is a reason to evaluate the full
quality task separately before any timing promotion.

The service stayed on dynamic clocks; EMC clocks and scoped energy were not
available. The result covers one Orin, one IQ1_M artifact, one fixed 512/64
prompt shape and this opt-in configuration. It does not qualify other model
formats, longer generated outputs, default settings, cache resizing during a
request or other service workloads. No defaults changed.

Reproduce with:

```sh
python3 tools/integration/cache_context_screen.py \
  --config bench/results/2026-10-14-phase6-q6-cache-context/base-config.json \
  --workloads bench/results/2026-10-14-phase6-q6-cache-context/workloads.json \
  --output bench/results/2026-10-14-phase6-q6-cache-context/block-NN \
  --cache-values 3000 5000 --context-values 8192 16384 \
  --rounds 3 --seed SEED --timeout 1800 --no-trace
```

Run each block under the recorded 28-GiB systemd scope. `SHA256SUMS.txt` records
the captured inputs, tools, executable and result files; model files remain in
`~/models/` and are not part of this repository.

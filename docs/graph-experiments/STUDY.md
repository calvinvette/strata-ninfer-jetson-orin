# Parametric and multivariate study

This supplements [the inherited protocol](../integration/BENCHMARKS.md).
For this campaign the causal control is the frozen **G0 JP7/NInfer candidate**, not the historical Strata commit.
All domains below are planned parameters, not implemented command-line flags.

## Model cohorts

| Cohort | Required? | Purpose |
| --- | --- | --- |
| Coder IQ1_M | Yes | Existing coding throughput/residency baseline |
| Coder Q2_0 | Yes | Existing packed expert/backend comparison |
| Original ISTA-DASLab IQ3_S | Yes | Existing full-model quality/reference cohort |
| Original ISTA-DASLab IQ2_XS | Optional | Lower-byte full-model residency versus IQ3_S |
| Original ISTA-DASLab IQ3_XXS | Optional | Intermediate full-model quality/traffic tradeoff |

Additional formats require verified availability, exact upstream model revision, pack checksum and executable codec.
Prefer identical parent weights for quant comparisons; report any pruning/fine-tuning differences.
Original versus Coder comparisons are model comparisons, not isolated quantization effects.
Do not download/convert large artifacts merely to enumerate cells.
Weight quant, KV quant and recurrent-state quant are three independent factors.
Use the inherited actual artifacts, not another file with a similar quant label.

## Workload blocks

Historical bridge: 557 prompt / 64 output at 8K capacity; also 512/64 and 2048/128.
Report natural EOS and actual counts, with fixed-work microbenchmarks kept separate.
Capacity screening retains configured 1K, 2K, 4K, 8K, 16K, 32K, 64K, 128K, 256K.
Configured capacity is not actual prompt length. Near-limit probes are sequential feasibility tests.

Agent blocks: versioned system/agent/instruction/skill/MCP scaffolding plus held-out coding requests;
stable-prefix fractions 0/50/90/99%; actual input 2K/8K/32K/128K where admitted;
10/50-turn sessions; code edits, tool JSON, novel code, test repair and retrieval.
Include beginning-injected session IDs, permutations, changing tools and mid-session repository edits.
Replay traces for controlled performance; execute held-out task tests for useful-work outcomes.
Never use future outputs or held-out solutions to seed retrieval/speculation.
Primary concurrency is one live request; multi-live is deferred until existing state gates qualify it.

## Screening domains

| Phase | Factors / levels | Nominated interaction |
| --- | --- | --- |
| G0 | Backend Strata/NInfer-supported; MTP 0/2/4; chunk 32/64/128; safe cache cap 50/75/100% | chunk × cache; MTP × workload |
| G1 | Prefix hit 0/50/90/99%; checkpoint cap 0/256/512/1024 MiB; stable/permuted/ID-first layout | hit × restore cost; cache cap × expert residency |
| G2 | proposer off/MTP/suffix/hybrid; draft length 1/2/4/8; suffix context 8/32/128 tokens | proposer × workload; length × acceptance |
| G2 ranker | hidden only / hidden+ngram / hidden+ngram+sketch; sketch width 16/32/64 | sketch cost × accepted length |
| G3 | policy LRU/frequency/cost-graph; lookahead 0/1/2/4; graph+row cache cap 64/256/512 MiB | lookahead × cache; policy × task phase |
| G4 | state FP32/FP16/INT8 mixed; window 1/4/8/16; protected channels 0/1/5%; rollback length 2/4/8 | precision × window; protection × horizon |
| G4 parked | raw/fixed-bit/entropy/transform; snapshot spacing 16/64/256 tokens | compression × restore/replay frequency |
| G5 | delta rank 8/16/32/64; expert groups 1/4/16 per layer; direct/materialized; resident cap 25/50/100% safe budget | rank × execution; grouping × quality |
| G6 | memory slots 32/64/128/256; graph hops 1/2; literal budget 256/1024/4096 tokens; frozen/adapter | slots × literals; memory × draft head |
| G7 | QSA memory in 1/3/6 selected layers; generated-state rank 8/16/32; fragment repair 0/10/25/100% | interface × length; repair × permutation |
| G8 | qualified components off/on in selected combinations | four interactions listed in PLAN |

These are screening ranges, not a full Cartesian launch.
Treat INT4, DCT/FFT and graph-generated experts as separately budgeted extensions.
Run cache-state blocks explicitly: cold process, warm weights without prefix hit, warm exact-prefix hit.
Record OS page-cache/storage state; do not claim cold disk from process restart alone.
KV control/candidate (existing supported Q4/K8V4 paths) is a separate long-context allocation block.
A successful gpu-unlock port is optional later off/on blocking, never bundled into G0 without recording it;
compare matched clocks/power and actual eligible kernels. No port is implemented by this plan.

## Sequential design and stopping

1. G0 fixes a functional profile per supported cohort, and measures same-backend noise.
2. Use a small full factorial for two or three factors. Larger domains use a preregistered fractional
   factorial or space-filling design; retain design seed, matrix, aliasing and excluded cells.
   Fit only identifiable main effects and nominated interactions; inspect rank and residuals.
3. One consistent warmup, three independent randomized A/B process blocks for screening.
   Confirm on at least seven new paired blocks and held-out tasks; increase samples if uncertainty
   prevents a decision. Thirty requests minimum for serving-tail claims.
4. Randomize within day/thermal/model/cache blocks. Bootstrap paired blocks or whole agent sessions,
   not tokens. Report median within-pair effects and 95% intervals.
5. Refine near useful regions, then lock configuration before final holdout. Keep tuning and final
   evaluation separate and acknowledge multiple comparisons; exploratory winners are not confirmations.
6. Stop on correctness, headroom, OOM, invalid telemetry or watchdog failure; preserve partial records.
   Use pass/fail/unsupported/pressure_abort/not_run with reasons, never fabricated zero throughput.

## Metrics and preregistered acceptance

Store PP tok/s for tokens actually computed and effective prompt tokens/s separately.
Store client TTFT, first visible answer, committed TG, total latency, rounds, draft acceptance,
replay/restore/encode costs, task success, repair turns and tokens, joules/successful task,
named power-rail scope, minimum physical headroom, peak swap, expert hits and physical/logical I/O.
Time unsuccessful tasks and report their counts; do not hide them in successful-task averages.

Default performance target: >=5% improvement in the declared end-to-end primary metric with a paired
95% interval excluding no gain; <=5% regression in other primary metrics unless a recorded Pareto tradeoff.
Exact paths require codec, accepted-prefix state and semantic continuation contracts.
For approximations, preregister a <=2 percentage-point absolute held-out task-success degradation budget
with confidence bounds, and zero tolerated critical tool-argument/instruction violations in the suite.
An underpowered quality interval is inconclusive, not a pass. State/logit error thresholds must be
calibrated on G0 and recorded before candidate confirmation; no universal L2 tolerance is assumed.
Baseline variability remains a confounder until characterized.

Every result needs run ID, phase/branch/source/binary, baseline ID, artifact hashes, graph snapshot,
corpus split, factor values, exact commands, actual backend/fallbacks, sampling seed, clock/thermal/cache
metadata, raw observations and status/reason. Include preprocessing/training/index-build cost and
amortization horizon separately from serving cost. Reproduce selected profiles in a clean process.

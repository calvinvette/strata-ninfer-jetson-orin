# Measurement and experiment protocol

## Controls and comparability

The primary control is Strata Orin `0be090c` on the **same Jetson and same day** as
the integration candidate, with identical verified weights, activation and KV
formats, tokenizer/template, prompt tokens, output policy, context reservation,
cache policy and clock profile. Preserve the disabled-feature route as a second
regression control where it differs from the pinned commit.

NInfer's 27B groupwise-int and 35B-A3B v2 artifact runs are separate reference
cohorts. Their throughput is not a speedup denominator for Flash-Next Coder IQ1_M.
Comparison across weight formats needs a measured quality constraint and a label
describing the mismatch. Historical Strata clocks were unlocked; historical NInfer
fixed-clock results cannot be joined into a causal performance comparison.

Every campaign has a metadata record: source/binary hashes, compiler flags, model
revision/checksums and format version, actual quantization, tokenizer/template,
JetPack/CUDA/driver, kernel/OS, storage, power mode and observed CPU/GPU/EMC clocks,
sampling settings, cache state, background services, warmup and repetitions.
Use explicit paths; no artifact selection by newest file or glob.

## Metrics and aggregation

| Scope | Raw observations | Required summary |
| --- | --- | --- |
| Request | Prompt/output counts, preparation, prefill, first-token and total times; streaming token timestamps | Median prefill and decode tokens/s, median TTFT; p95 request latency with sample count; prefill proxy labeled separately from client TTFT |
| Speculation | Drafted/accepted counts, target/draft/verify times, rounds, fallback count | Accepted/drafted ratio with both counts; emitted tokens/round; cost per emitted token |
| Operator | Warm/cold latency samples, shape/format, registers, shared memory, spills, occupancy | Median and p95 ms, dispersion, measured bytes/s; mathematical work and representation stated |
| Physical memory | MemAvailable, cgroup current/max, CUDA free, process-tree RSS, swap, faults | Minimum available RAM, peak usage/swap, allocation/reservation bytes by owner; RSS is not total GPU-inclusive usage |
| Experts/storage | Slots/bytes, hits/misses, logical bytes, transfer time, physical disk deltas | Hit rate with counts, allocation, bytes/request, transfer stalls; host-wide I/O labeled with background contamination |
| Power/thermal | Timestamped temperatures, clocks, throttling and named rail power | Window energy, joules/token, tokens/joule, average/peak power; `VDD_GPU_SOC` never labeled whole-board energy |
| Correctness | Reference/output logits and state, exact codec/layout checks, finite values, API/recall/scoring results | Error norms, selected-token/logprob error and justified tolerance; pass/fail/skip by actual contract |
| Capacity/service | Actual prompt+generation, allocation, pressure aborts, recovery, queue/wait times | Largest completed and recovered point; abort boundary separate; throughput and per-request fairness only for implemented concurrency |

Measure request stages with a monotonic clock and align telemetry to those windows.
Decode rate excludes prefill; state the treatment of the first token. In operator
timings use CUDA events and completion synchronization; distinguish kernel time
from host enqueue time. Measure startup separately from steady state.

For each homogeneous cell and engine, take the median of **per-request** rates.
Do not average rounded medians or combine token counts from different workloads.
For paired effects, compute within-block candidate/control ratios (or latency
deltas) and report their distribution with a paired bootstrap interval. A ratio of
displayed medians is acceptable as a descriptive column, labeled as such; it is
not the paired effect estimator. Retain raw values at full precision.

Three measured runs after one warmup are screening only. Use at least seven
independent request/process blocks for confirmation, expanding only if uncertainty
changes the decision. Report p95 as descriptive with small samples; use at least
30 independent requests for serving-tail claims. Bootstrap whole paired blocks,
not tokens or telemetry samples. Record zero output, early EOS and failed runs;
never substitute zero throughput for a skipped/aborted cell.

## Sequential experimental design

The machine-readable [campaign](../../bench/integration/campaign.json) describes
planned cells, **not supported engine flags or completed results**. The planner
enumerates cells and randomized baseline/candidate pairs without running them.
An execution adapter must prove each `required_capabilities` entry, translate
abstract factors to real flags, check memory feasibility and preserve those exact
commands. Unavailable combinations are `unsupported`, never silently substituted.

| Stage | Factors | Design and question |
| --- | --- | --- |
| Controls | Workload, source revision | Repeated same-day pairs: is the harness stable? |
| Speculation screening | MTP 0/2/3/4 × KV control/candidate × pp512+tg64 / pp2048+tg128 | Full small factorial; does the best draft window depend on workload or KV? |
| Resource screening | Context 8K/32K/64K × expert-cache cap 50/75/100% of safe automatic allocation × prefill 32/64/128 | Constrained factorial; cache/workspace and context interactions; reject before launch if budget fails |
| CPU/transfer screening | Workers 1/2/4/8 × device-copy/mapped-read policy | Paired factorial on qualified buffers; memory bandwidth contention and ownership correctness |
| Graph interaction | Eager/graph × MTP 0/2/4 × short/long workload | Test graph/speculation interaction only on qualified decode routes |
| Kernel schedule | Row 16/32/64 × column 64/128 × stages 2/3/4, selected token shapes | Compile/resource admission before numerical qualification and timing; no resident-grid assumptions |
| Capacity | Reservation 1K–256K; actual near-limit prompt; short recovery | Sequential feasibility, not a throughput optimization factorial |

Clock/toolchain/model are **blocking variables**, not hidden candidate changes.
Randomize cell order within a day/thermal block; alternate or randomize A/B within
each pair. Use warmup consistently, define warm versus cold cache explicitly and
do not drop the host page cache or stop unrelated services without task authority.
Prefer a thermal equilibrium criterion (stable temperature and clock distribution)
over an arbitrary short sleep. Keep the thermal and cache state with each block.

Start with the small factorials above. If a larger space is warranted, choose a
documented fractional factorial or space-filling design with identifiable main
effects and nominated two-factor interactions. State aliasing and do not fit more
coefficients than independent design points. Candidate models can use log latency
or log throughput with context, cache, chunk, workers and selected interactions.
Inspect rank, residuals and held-out predictions; a model does not replace measured
confirmation. Refine numeric ranges near promising regions, then confirm on new
prompts and sizes instead of selecting and evaluating on the same cells.

## Promotion and plots

Before a confirmation run, record a minimum useful effect and regression budget
for the intended profile. Initial proposed rule: at least 5% median improvement
in the nominated end-to-end metric, paired 95% interval excluding no improvement,
no more than 5% regression in the other primary latency/throughput metric, no
quality contract failure and no headroom violation. These are project decision
thresholds, not measurements; a different tradeoff requires a written decision.
Capacity improvements may instead qualify a previously infeasible request while
meeting its explicit latency and quality budget.

Publish the Pareto frontier for latency, decode rate, memory and energy; present
quality and feasibility as constraints. Include rejection reasons and ablations
for each promoted component and their combined configuration.

Required figures use the exact table cells and statistics:

- Paired baseline/candidate median PP and TG versus context, faceted by prompt size.
- TTFT and decode versus MTP window, faceted by KV and workload, with uncertainty.
- Context × cache and chunk × cache heatmaps; infeasible cells clearly marked.
- Throughput/TTFT versus headroom and joules/token Pareto plots.
- Allocation/peak-swap/minimum-RAM and disk totals in panels labeled with their
  actual aggregation; never present maxima or totals as medians.
- Sustained throughput, clocks, temperature and headroom over elapsed time.

Extend the existing
[Strata plotting script](../../bench/results/2026-10-08-jetson-orin/plot_context_comparison.py)
and NInfer report tools after a result adapter exists. Export PNG/SVG plus CSV/JSON
for each table; no interpolated values for missing cells and no invented baseline
for an unmatched near-limit run. Phase 1 produced paired control plots; those show
same-source screening variability and are not optimization comparisons. Candidate
performance plots require the later qualified, paired experiment cells.

## Running safely and reporting limits

Only one model campaign uses the board at a time. Retain 6 GiB available physical
RAM for ordinary integration runs and check cgroups/CUDA ceilings separately.
The copied NInfer `run_with_host_pressure.py` is a reference: its default is 1.2
GiB and its termination path can wait indefinitely after SIGTERM. Phase 1 must
adapt it with prelaunch checks, bounded TERM-to-KILL escalation, whole-child-group
cleanup, signal handling and durable partial results before unattended campaigns.
Do not run its original defaults as the integration policy.

Record `pass`, `fail`, `unsupported`, `pressure_abort` or `not_run` for every planned
cell and retain the reason. Pressure aborts do not establish capacity. Model
changes, quantization changes, rail-only energy, dynamic clocks, swap and unmatched
cache state must remain visible in conclusions. x86 HIP/SYCL build evidence is
portability evidence and cannot validate ARM performance or GPU model execution.

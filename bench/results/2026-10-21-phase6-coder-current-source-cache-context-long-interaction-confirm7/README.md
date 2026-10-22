# Coder IQ1_M held-out cache × context interaction confirmation

This seven-block randomized confirmation crosses requested expert-cache
arguments 1,500/3,000 MiB with configured contexts 8,192/16,384 using the same
held-out 7,501-token retrieval/arithmetic prompt in every cell. The task must
fit within the 8K cell: expected usage is exactly 7,501 prompt tokens and 48
completion tokens. Each independent fresh-service cell uses one warmup and one
measured request; block, not token or request repetition within a cell, is the
unit for paired uncertainty. One 28-GiB cgroup limit is applied per service
cell and the six-GiB physical host-availability floor remains in force.

The current Strata binary, model revision, shards, profile, request oracle and
host paths are pinned in `design.json`, `config.json`, `workloads.json` and
`model-sha256.txt`. No model is downloaded or copied by this campaign.

Run or safely resume with:

```sh
bash bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/run_interaction_confirm7.sh
```

The runner preserves complete blocks and refuses to overwrite an incomplete
block. The campaign is in progress; no interaction estimate is available
until all seven blocks and the exact-answer, token-count, clock and memory
audits pass. The analyzer checks each four-cell block remains within one local
day and reports observed CPU/GPU clocks and `tj` temperature ranges. Named
tegrastats rails may be integrated separately and include board idle/background
power; they are not process energy.

Block 1 completed all four randomized cells with exact answers and 7,501/48
prompt/completion token counts:

| Requested cache | Context | Client time | Prompt/decode tok/s | Minimum host/admission GiB |
| ---: | ---: | ---: | ---: | ---: |
| 1,500 MiB | 8K | 365.7 s | 20.7 / 12.2 | 17.99 / 16.72 |
| 3,000 MiB | 8K | 310.5 s | 24.5 / 13.0 | 14.29 / 14.29 |
| 3,000 MiB | 16K | 308.9 s | 24.6 / 13.1 | 14.11 / 14.11 |
| 1,500 MiB | 16K | 335.1 s | 22.7 / 12.0 | 17.62 / 17.60 |

The single-block cache reduction in client time was 15.1% at 8K and 7.8% at
16K. The cache-by-context ratio-of-ratios was +8.6% for latency, meaning the
cache benefit was smaller at 16K in this block. These are descriptive values
with no inferential weight until the seven-block campaign completes. Every
cell remained above the six-GiB floor, with zero sampled cgroup events. The
partial analyzer also reports GPU clocks 306–1,300.5 MHz, CPU clocks
729.6–2,201.6 MHz, and `tj` 50.1–59.7 °C; EMC clock access was unsupported.
The analyzer reports interim point estimates but withholds bootstrap intervals
until all seven paired blocks pass. Block 2 completed all four randomized cells with the exact answer and
7,501/48-token usage. Client times were 334.4/307.9 s (1,500/3,000 MiB) at
8K and 333.7/310.7 s at 16K. Minimum host/admission availability across the
block was 14.05 GiB; all cells stayed above the six-GiB floor and all 2,579
sampled scoped-cgroup records had zero low/high/max/OOM/OOM-kill events.

Block 3 completed all four randomized cells with exact answers and token
counts. Client times were 335.5/308.8 s (1,500/3,000 MiB) at 8K and
333.7/309.4 s at 16K. Minimum host/admission availability was 14.10 GiB; all
2,555 scoped-cgroup samples had zero events.

Block 4 completed all four randomized cells with exact answers and token
counts. Client times were 336.4/306.6 s at 8K and 334.3/310.1 s at 16K
(1,500/3,000 MiB). Minimum host/admission availability was 14.06 GiB; all
2,555 scoped-cgroup samples had zero events.

The interim analyzer recognizes four complete paired blocks. Cache latency
reductions are 8.41% at 8K and 7.25% at 16K; the cache-by-context latency
interaction point estimate is +1.45%. Confidence intervals remain withheld
until all seven blocks pass. Block 5 has started with its randomized 3,000-MiB/16K cell. Warmup and measurement passed in 370.4/308.8 s with the exact answer and
7,501/48-token usage. Minimum host/admission availability was 13.93/13.93 GiB;
all 663 scoped-cgroup samples had zero events. The randomized 1,500-MiB/8K cell passed in 346.5/335.9 s
(warmup/measurement), with the exact answer and 7,501/48-token usage. Minimum
host/admission availability was 17.98/17.31 GiB; all 663 scoped-cgroup
samples had zero events. The randomized 1,500-MiB/16K cell passed in 390.9/334.5 s
(warmup/measurement), with the exact answer and 7,501/48-token usage. Minimum
host/admission availability was 17.63/17.63 GiB; all 703 scoped-cgroup
samples had zero events. The randomized 3,000-MiB/8K cell passed in 323.5/310.6 s
(warmup/measurement), with the exact answer and 7,501/48-token usage. Minimum
host/admission availability was 14.25/14.25 GiB; all 620 scoped-cgroup
samples had zero events. Block 6's randomized 1,500-MiB/16K cell passed in
346.3/334.4 s (warmup/measurement), with the exact answer and 7,501/48-token
usage. Minimum host/admission availability was 17.79/17.10 GiB; all 662
scoped-cgroup samples had zero events. The randomized 1,500-MiB/8K cell passed
in 345.4/334.5 s (warmup/measurement), with the exact answer and 7,501/48-token
usage. Minimum host/admission availability was 18.01/17.10 GiB; all 662
scoped-cgroup samples had zero events. The randomized 3,000-MiB/16K cell passed in 320.5/308.5 s
(warmup/measurement), with the exact answer and 7,501/48-token usage. Minimum
host/admission availability was 14.12/14.12 GiB; all 615 scoped-cgroup
samples had zero events. The final randomized 3,000-MiB/8K cell passed in
320.2/308.0 s (warmup/measurement), with the exact answer and 7,501/48-token
usage. Minimum host/admission availability was 14.31/14.31 GiB; all 616
scoped-cgroup samples had zero events. Block 6 now has four passing cells.
The randomized block 7 1,500-MiB/8K cell passed: its warmup/measured client
totals were 346.3/395.0 s, with exact answer and 7,501/48-token usage. Minimum
host/admission availability was 18.00/16.57 GiB; all 718 scoped-cgroup samples
had zero events. The randomized 3,000-MiB/8K cell passed with warmup/measured
client totals 352.8/308.4 s, exact answer and 7,501/48-token usage. Minimum
host/admission availability was 14.20/14.20 GiB; all 648 scoped-cgroup samples
had zero events. The randomized 1,500-MiB/16K cell passed with warmup/measured client totals
347.1/334.2 s, exact answer and 7,501/48-token usage. Minimum host/admission
availability was 17.65/17.37 GiB; all 662 scoped-cgroup samples had zero
events. The randomized 3,000-MiB/16K cell passed with warmup/measured client totals 323.0/310.4 s, exact answer and 7,501/48-token usage. Minimum host/admission availability was 13.94/13.94 GiB; all 619 scoped-cgroup samples had zero events. The interim
analyzer recognizes six complete blocks; cache effect in client total time is
7.94% at 8K and 7.49% at 16K. Confidence intervals and interaction
conclusions remain withheld until block 7 passes.
The original block 7 completed all four cells, but crossed local midnight
(October 21–22) and is excluded from paired inference; its raw results remain
preserved. The separately randomized same-day replacement (seed 2026102227) is
stored in `per-cell-scopes/block-07-replacement/` and is the seventh source used
by `analyze_interaction.py`. All 28 measured cells across the seven analyzed
blocks passed exact answer and 7,501/48-token checks. The replacement cells also
passed, with warmup/measured client totals of 377.6/365.1 s (1,500 MiB/8K),
345.7/335.2 s (1,500 MiB/16K), 321.0/308.4 s (3,000 MiB/16K), and 322.0/308.3 s
(3,000 MiB/8K). Its minimum host/admission availability was 14.09 GiB; all
2,612 scoped-cgroup samples had zero events. The full analyzer passed for blocks
1–6 plus the replacement, with 18,126 telemetry samples and no errors.

For this held-out task, 3,000 MiB versus 1,500 MiB reduced median paired client
total latency by 7.95% at 8K context (95% paired-block bootstrap interval
7.93%–15.11%) and 7.71% at 16K (7.23%–7.82%). The cache-by-context interaction
was +1.12% (95% interval +0.22% to +8.58%). The 8K interval is wide, reflecting
block variability including a 395.0 s measured request at 1,500 MiB/8K. This
result confirms the cache effect and estimates a small interaction for this
model, source, profile and workload; it does not promote a general serving
profile or close Phase 6's other interactions, broader response-model and energy/Pareto work. Dynamic
clocks were sampled; EMC frequency was unsupported. Across analyzed blocks,
minimum host and admission availability were both 13.93 GiB, with zero cgroup
pressure, limit or OOM events. The exact source, binary and model identities are
pinned in `design.json`; the original cross-midnight block remains available
for audit but is excluded from the analyzer.

## Block-adjusted log-response model

The planned response-model check uses log latency/throughput with cache,
context, their interaction, and seven paired-block fixed effects. The balanced
design is full rank (10 parameters, 18 residual degrees of freedom). A
10,000-replicate whole-block bootstrap is in `response-model.json`; its
reproduction script is `analyze_response_model.py` and uses only the Python
standard library. For client total latency, the model estimates a −8.87%
cache ratio (3,000/1,500 MiB; cluster-bootstrap interval −10.19% to −7.65%),
a −1.26% context ratio (16K/8K; −2.72% to +0.07%), and a +2.97% context
interaction (+0.56% to +5.67%). This interaction is a mean-log contrast; the
paired-block median ratio-of-ratios in `analysis.json` remains the primary
estimate (+1.12%, +0.22% to +8.58%). The direction agrees, while the difference
in estimand and the wide paired interval counsel against treating the model as
a precise effect size.

The 28-row model had full rank for all four outcomes. Maximum internally
studentized residuals were 2.73 for client total, 2.74 for TTFT, 2.74 for
prompt throughput, and 3.93 for decode throughput. The decode model exceeds
the exploratory absolute-3 screen at block 7 / 1,500 MiB / 16K. Keep the
paired-block bootstrap primary and the model diagnostic; this fit does not
support changing a serving default. No new energy claim is made.

Re-run the model after `analyze_interaction.py` passes:

```sh
python3 bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/analyze_response_model.py
```

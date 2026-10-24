# MTP3 near-limit prompt screen — Orin — 2026-10-23

Three randomized paired blocks compared MTP off and MTP3 on the 7,501-token
Coder IQ1_M retrieval/arithmetic workload. Each cell ran in a fresh process
with one shared distinct 512-token warmup, prompt caching disabled and up to 48
generated tokens. All six processes and API requests passed; paired response
content matched in all blocks. The harness confirmed matching non-MTP arguments,
KV format and expert residency.

MTP3 drafted 34 tokens and accepted 28 in each block. Its decode-throughput
delta median was **-6.01%** versus MTP-off (paired-block bootstrap 95% interval
-6.08% to -5.56%); individual deltas were -6.08%, -5.56%, and -6.01%. Median
TTFT increased 0.62%; median total request time increased 0.67%. In contrast,
the same MTP3 setting showed +4.34% median decode throughput in a seven-block
replication on the 512-token prompt. The sign change is evidence that MTP
performance depends on prompt/workload length for this setup; it is not a
universal MTP3 regression or win. Since each response emits 45 tokens, the
long request is prefill-dominated, so decode-throughput movement contributes
little to total request time.

Minimum observed physical/admission availability was 16.93 GiB, above the
6 GiB floor; sampled cgroup memory-event counters were zero. The retained
tegrastats records show junction temperatures from 53.0–60.5 °C and GR3D
utilization from 0–99%. CPU clocks, named power rails, and temperature samples
are recorded, but GPU clock frequency readback was unavailable. Rail energy was
not integrated; the three blocks are not thermal steady-state qualification.

## Scope and identity

- Source HEAD at run launch: `cb0a3910`.
- Device: Orin AGX, native aarch64, CUDA runtime path, shared physical RAM.
- Model: Coder IQ1_M two-shard GGUF with the upstream base-checkpoint MTP
  weights under `~/models/strata-orin-validation/mtp/rt`.
- Workload: `coder-mtp4-heldout-retrieval-arithmetic-near-limit-7501`, exact
  prompt and expected response in `selected-workloads.json`. This is a distinct
  prompt length from the 512-token screen, but was used in prior MTP4 research;
  it is not a novel held-out model/workload cohort.
- Seed: 20261025; MTP windows randomized within blocks.
- `campaign.json`, per-cell configurations, raw requests, engine/supervisor
  logs, memory samples, tegrastats and `SHA256SUMS.txt` retain the evidence.

This screen tests timing and paired response-content parity only. It does not
record persistent accepted-prefix state, establish a general quality bound, or
qualify long-chain adaptive behavior. It does not promote a default. Phase 5
remains open; Phase 6 still needs independent held-out prompts, confirmation
repetitions and broader graph/KV/Pareto/energy analysis.

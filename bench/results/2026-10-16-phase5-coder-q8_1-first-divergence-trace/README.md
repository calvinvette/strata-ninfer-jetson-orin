# First Coder activation divergence trace — 2026-10-16

This supervised four-pair diagnostic localizes a route-dependent numerical
difference in the Coder IQ1_M service. It compares the default CPU expert-row
path with the opt-in CPU mirror of CUDA Q8_1 row arithmetic. Both arms used the
same current Strata binary (SHA256
`d2a1928053a1a7e01930490c26f53621016c91749151781b13bf33c7f844f661`), source
revision `5877d08f`, model snapshot
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M, and identical prompt hashes
recorded in each arm's `result/analysis.json`. Each trace captured all 48
layers for dispatches 1392–1583. The four pair seeds were 20261020, 20261021,
20261022 and 20261024; the first three ran default first, and the fourth ran
the mirror first. All eight arms passed. This is a repeated correctness
diagnostic, not a performance estimate.

In all four pairs, the first all-layer activation difference was dispatch
1394, layer 2. Expert
IDs and owner decisions still matched between arms. The preceding dispatch
(1393, layer 1) had bitwise-identical input activations and the same selected
experts and owners. Four experts were CPU-owned: 209, 207, 85 and 153; all use
IQ2_S gate/up weights and Q2_0 down weights. On the exact captured layer-1
activation, the native parity tool compared each expert's default CPU result
and Q8_1 mirror result against CUDA. The default path differed from CUDA in all
7,680 output words per expert, with relative L1 errors from 1.23e-2 to
1.57e-2. The mirror matched CUDA bitwise for all four. Both CPU routes remained
within the tool's independent dequantized GGML reference bound. The parity
binary SHA256 is
`5cc9202f3c4e51266bcb725ca2ea0111b0911bc492df2325455bdd19a3b7a5c2`.

The layer-2 activation difference had maximum absolute error 0.00917423 and
relative L1 0.00380745 in every pair. Service behavior did not become
equivalent after the operator match: every pair differed at 3 of 16 generated
token positions on the 2,048-token request and 13 of 16 on the subsequent
identical 512-token continuation. The initial short response and immediate
recovery response matched in every pair. This supports CPU-row arithmetic as a cause of an early hidden
activation difference, but does not establish it as the only cause or show
that mirroring it corrects persistent state, continuation behavior, quality,
or speed. The route remains opt-in and Phase 5 remains open.

All eight supervised runs passed with 1,596 one-second memory samples total.
The minimum host/admission availability across all arms was 14.354/14.354 GiB,
above the six-GiB floor, and no cgroup memory events were recorded. Clocks were
observed read-only. Energy was not attributed to requests, and timings are not
compared.

Each pair used adaptation cadence 4, swap budget 8, prompt cache disabled and
one continuation. Commands and actual arm order are retained in each
`pairN/*/supervisor/result.json` and `pairN/campaign.json`; full traces,
outputs, telemetry and per-expert parity logs accompany this report. Reproduce
one pair with:

```sh
python3 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/run_trace_pair.py \
  --output bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/reproduction
python3 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/run_operator_checks.py \
  --output bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/reproduction/operator-checks
```

The retained four-pair summary is regenerated and contract-checked with:

```sh
python3 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/analyze_repeats.py
```

`analyze_trace.py` reproduces the detailed pair-1 operator report.

## Actual service CPU-row capture

The four-pair traces established that dispatch 1393/layer 1 had identical
inputs, expert IDs and owners in both routes; the standalone operator test
then showed the CPU mirror's expert output matches CUDA. To verify that the
service itself produced the same row-level change, a fifth supervised pair
captured the CPU output buffer immediately after expert-pool execution at
dispatch 1393/layer 1. It used the same model, prompts and Q8_1 opt-in. The
mirror ran first. Both arms passed; minimum availability was 14.474 GiB over
385 one-second samples, with no cgroup memory events.

The actual service outputs for experts 209, 207, 85 and 153 differed across
all 2,560 values per row. Relative L1 deltas were 0.012306, 0.015658, 0.012738
and 0.013444, matching the standalone default CPU-versus-CUDA deltas to
reported precision. This establishes that the route arithmetic difference is
present in the actual service CPU rows before the weighted MoE combine. It
does not establish that the combined output or downstream recurrence matches
the accelerator path. The per-row capture is opt-in and adds no default-path
behavior; the targeted service still showed the same 3/16 long and 13/16
continuation token differences.

The actual-service row comparison is reproduced from retained data with:

```sh
python3 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/analyze_cpu_outputs.py
```

The pair used for this output capture can be reproduced with:

```sh
python3 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/run_trace_pair.py \
  --seed 20261026 --capture-cpu-outputs \
  --output bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/reproduction-cpu-outputs
```

The updated CUDA binary SHA256 was
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`.
Orin's 16 native-expert parity CTests passed after the rebuild. On maestro1,
the shared `src/core/expert_source.cpp` overlay compiled and linked into the
HIP service and its CLI help check passed; the raw build log and binary hash
are retained under `backend-checks/`. SYCL selects its separate migrated
`sycl/src/core/expert_source.cpp`, which this diagnostic did not modify; its
current-source service build required no work. Neither maestro1 check is
accelerator runtime evidence.

Model payloads remain under `~/models/`; only provenance and captured numerical
evidence are in this repository. `SHA256SUMS.txt` covers the artifacts,
excluding itself.

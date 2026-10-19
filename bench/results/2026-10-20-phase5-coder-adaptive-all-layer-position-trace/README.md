# Coder adaptive migration all-layer trace and IQ3_XXS/Q2_0 mirror — Orin — 2026-10-19

This experiment used the current Orin candidate and the pinned Coder IQ1_M
artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. The model and pack remain under
`~/models/strata-orin-validation/`. Both paired service runs used the same
512→2,048→512→continuation sequence, 16 tokens per request, accepted-only
adaptive accounting, and `STRATA_NATIVE_CPU_Q8_1_DOT=all`. The comparison was
randomized and supervised with `MemoryMax=28G`; it is a correctness diagnostic,
not a timing or quality comparison.

The new `STRATA_CAPTURE_MOE_POSITION` filter captures the same absolute
verifier position across all layers. At position 511, each arm retained 96
rows: one initial-short row and one recovery-short row for each of 48 layers.
The original selector did not include the model's IQ3_XXS/Q2_0 layer pair. In
that run, the initial and recovery activations and expert IDs matched through
layer 12, expert 141 changed owner from CPU to GPU at layer 12, and layer 13
was the first captured activation that differed. Delayed adaptation had no
activation differences across the same layers.

I extended the opt-in Q8_1 route to IQ3_XXS/Q2_0. The exact layer-12 expert 141
then matched the CUDA expert output bit-for-bit on the captured activation at
token widths 1 through 8. Actual layer-1 IQ2_S/Q2_0 expert 1 and layer-3
IQ2_S/IQ4_NL expert 1 also matched bit-for-bit at widths 1 through 8. The
selector contract, single-row, and multi-token tests passed 3/3. The real
activation is serialized with nine significant decimal digits, enough to
round-trip its FP32 values.

The repeated service pair with the expanded selector improved output parity:
all four request outputs matched exactly across the delayed and adaptive
services, and adaptive short recovery returned the same 16 tokens as its
initial short request. The state result still fails parity. Delayed short
recovery matched all 16 accepted-prefix states with its initial short request;
adaptive recovery differed at all 16. Across arms, all 16 recovery token IDs
matched but all 16 state records differed. The first changed captured
activation moved to layer 26; layer 25 had the same activation and expert IDs
and no owner changes. The trace does not identify the remaining upstream state
or operator cause. The selector remains opt-in and is not a migration fix.

| Arm | Run time | Minimum host/admission availability | Swap byte/residency checks | Result |
| --- | ---: | ---: | ---: | --- |
| Delayed control | 320.1 s | 14.00 / 14.00 GiB | 0 / 0 | Recovery output and all 16 states matched initial short |
| Adaptive cap 8 | 199.7 s | 14.33 / 14.33 GiB | 15 / 15 | Recovery output matched; all 16 states differed |

Both supervisors passed, with zero cgroup low/high/max/OOM/OOM-kill events.
The all-layer captures and complete memory/clock samples are retained under
`run/` (the original selector) and `run-with-iq3xxs-q2_0/` (the expanded
selector). `all-layer-analysis-before-iq3xxs-q2_0.json` and
`all-layer-analysis-after-iq3xxs-q2_0.json` independently compare all route
rows and accepted-prefix states. Real-weight operator output and CTest logs
are under `operator-checks/`.

The source patch was built on Orin CUDA/SM87. `file_expert_source_test` passed
1/1, and the new Q8_1 selector/single-row/multi-token CTests passed 3/3. The
full CTest suite was not rerun. maestro1 HIP/SYCL rebuilds could not start:
its root filesystem reported zero available bytes. No files were removed from
that host to make space; these backend checks remain outstanding. This change
does not alter default dispatch. `source-overlay.patch` records the uncommitted
selector changes relative to source commit `76eec469`; `SHA256SUMS` covers the
retained report, source overlay, operator checks and raw paired captures. Phase
5 remains open.

Reproduce the extended service pair on Orin with the current source and local
model artifacts:

```sh
cmake --build build/integration/candidate --target strata native_expert_parity --parallel 2
ctest --test-dir build/integration/candidate -R 'native_expert_parity_(iq3_xxs_q2_0_cpu_q8_1|q8_1_selector_contract)' --output-on-failure
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/reproduction \
  --seed 20261021 --run
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/analyze_trace.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/reproduction \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/reproduction-analysis.json
```

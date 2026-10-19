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

Per-layer GDN hashes narrow the state boundary further. At the first accepted
token of the adaptive recovery, GDN ordinals 20–35 differ from the initial
short request; ordinals 0–19 match. With this model's QSA interval of four,
ordinal 20 is GDN model layer 26. The delayed control matches all 36 GDN hashes
at all 16 accepted prefixes. This agrees with the first changed captured
expert input at layer 26, but hashes do not identify the operation that first
changed the GDN state. At layer 24, the only owner-flipped expert in this row
(expert 173, IQ2_S/IQ4_NL) independently matched CPU and CUDA output bit-for-bit
on both captured activations (0/7,680 F32 words differed in either run). The
separate standalone-MMVQ subdiagnostic still reports its documented schedule
difference. This single-expert result does not establish aggregate-layer or
full-model parity.

## Raw accepted-prefix GDN state follow-up

To measure the state delta without committing large state files, I captured the
initial short request at occurrence 1 and the recovery short request at
occurrence 2 in separate supervised reruns of the same adaptive sequence. Both
runs used the same candidate binary (`89b1f96e…`), config, model revision and
token IDs. The first request's per-GDN hashes matched exactly across the two
runs, and the recovery dump's per-layer hashes matched the service log at the
second position-511 accepted prefix. `compare_gdn_dumps.py` verifies each raw
dump against its logged FNV1a hashes and checks the initial hashes across runs.

At `L=512`, GDN ordinals 0–19 were bit-identical. Ordinals 20–35 differed in
12,921,960 of 13,074,432 float values (98.83% of those layers; 43.92% of all
GDN values). Overall relative L2 was 1.686%, with maximum absolute difference
1.403. Ordinal 20 (model layer 26) had a much smaller 1.15e-5 relative-L2
difference; subsequent changed GDN layers ranged from 0.80% to 3.49%. The
state change starts at the same model layer as the first changed captured
expert input and grows in later recurrent layers. These values describe the
two states; they do not establish which state is more accurate or identify the
operation that caused the first difference.

## Layer-25 CPU-row follow-up

The first changed captured expert-dispatch input is at layer 26. A further
same-sequence capture joined layer 25 at position 511 in separate initial and
recovery runs using the same binary (`89b1f96e…`). The layer-25 activation,
expert IDs and owners were identical. Its three CPU-owned expert rows (experts
30, 180 and 193) were bitwise identical across runs: 0 of 7,680 float values
changed. This rules out those captured CPU rows as the source of the first
layer-26 difference for this position. The layer-25 GPU rows, router weights,
shared expert and full weighted layer output were not captured, so the cause is
still unresolved.

Both supervised runs passed with `MemoryMax=28G`, zero scope memory events and
the six-GiB availability guard. They took 223.4 and 243.2 seconds, with minimum
host/admission availability of 14.22 and 14.24 GiB. Clocks remained dynamic;
this is correctness localization, not a timing comparison. The compact
service captures, full route traces, supervisor samples and comparison are in
`layer25-cpu-output-pair/`. Reproduce with dispatch IDs verified from the route
trace:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py --output /tmp/layer25-initial/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --capture-cpu-output-layer 25 \
  --capture-cpu-output-dispatch 169 --output /tmp/layer25-initial/run

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py --output /tmp/layer25-recovery/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --capture-cpu-output-layer 25 \
  --capture-cpu-output-dispatch 1993 --output /tmp/layer25-recovery/run

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer25_cpu_outputs.py \
  --initial /tmp/layer25-initial/run --recovery /tmp/layer25-recovery/run \
  --initial-dispatch 169 --recovery-dispatch 1993 \
  --output /tmp/layer25-cpu-output-pair.json
```

## Layer-25 verifier router and expert-parts follow-up

A same-service run captured the verifier router IDs and weights and all ten
expert output rows for model layer 25 at position 511 in both the initial and
recovery short requests. The token (271), expert IDs, and weights matched; all
25,600 FP32 values after `moe_hit_add` were bit-identical. This rules out the
captured routed expert contributions, including GPU-owned rows, as the source
of the later layer-26 difference for this position. Shared-expert output,
weighted combine, and residual write remain unresolved. This is still a
single-position correctness trace, not a fix or a performance result.

The new capture built on Orin, and four focused CTests passed. Its supervised
same-service run passed with 14.31 GiB minimum host/admission availability,
10.85 GiB maximum scope use, and zero cgroup events; duration was 184.9 s.
Clocks were dynamic, EMC readback was denied, and energy was not request-
attributed. Raw files and the analyzer output are under
`layer25-verifier-parts/`; the focused report documents the reproduction
command and graph-capture position-filter behavior. A current top-level
verifier HIP rebuild on maestro1 recompiled the changed file and passed its
help check; the SYCL overlay was unaffected and its build reported no work.
These are compile/CLI checks only. Phase 5 remains open.

The two raw 113 MiB dumps remain outside Git under
`~/models/strata-orin-validation/experiments/phase5-gdn-state/`; their full
SHA256 values and per-layer comparison are in `gdn-state-delta.json`. The
supervisor samples, service logs and matching route captures are retained in
`gdn-state-capture/`. Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/gdn-initial/supervisor --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --dump-gdn-occurrence 1 --output /tmp/gdn-initial/run

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/gdn-recovery/supervisor --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
  --adapt-every 4 --adapt-swaps 8 --dump-gdn-occurrence 2 --output /tmp/gdn-recovery/run

mkdir -p "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state"
cp /tmp/gdn-initial/run/gdn-state-L512.bin \
  "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-initial-L512.bin"
cp /tmp/gdn-recovery/run/gdn-state-L512.bin \
  "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-recovery-L512.bin"

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_gdn_dumps.py \
  --reference "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-initial-L512.bin" \
  --candidate "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-recovery-L512.bin" \
  --reference-log bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/gdn-state-capture/initial/run/service.log \
  --candidate-log bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/gdn-state-capture/recovery/run/service.log \
  --reference-occurrence 1 --candidate-occurrence 2 \
  --output /tmp/gdn-state-delta.json
```

| Arm | Run time | Minimum host/admission availability | Swap byte/residency checks | Result |
| --- | ---: | ---: | ---: | --- |
| Delayed control | 320.1 s | 14.00 / 14.00 GiB | 0 / 0 | Recovery output and all 16 states matched initial short |
| Adaptive cap 8 | 199.7 s | 14.33 / 14.33 GiB | 15 / 15 | Recovery output matched; all 16 states differed |

Both supervisors passed, with zero cgroup low/high/max/OOM/OOM-kill events.
The all-layer captures and complete memory/clock samples are retained under
`run/` (the original selector) and `run-with-iq3xxs-q2_0/` (the expanded
selector). `all-layer-analysis-before-iq3xxs-q2_0.json` and
`all-layer-analysis-after-iq3xxs-q2_0.json` independently compare all route
rows, accepted-prefix states, and per-GDN-layer state hashes. Real-weight
operator output and CTest logs are under `operator-checks/`.

The source patch was built on Orin CUDA/SM87. `file_expert_source_test` passed
1/1, and the Q8_1 selector/single-row/multi-token CTests passed 3/3; together,
the four focused CTests passed. The full CTest suite was not rerun. The current
source also passed the full 163-test integration Python suite. Current-source
HIP and SYCL builds on maestro1 passed compile/link and `strata --help` with
two jobs. The SYCL build consumed its `sycl/src/program/generate.cpp` overlay;
the GDN dump diagnostic was ported to that overlay and rebuilt, including its
per-kernel device-link step. Exact source hashes, binary hashes and logs are
under `backend/maestro1-current-source-2026-10-19/`; the SYCL overlay patch is
`sycl-gdn-state-capture.patch`. Maestro1 is x86_64, so these are build/CLI
checks only. This change does not alter default dispatch.
`source-overlay.patch` records the selector changes relative to source commit
`76eec469`; `gdn-state-capture.patch` records the state-dump diagnostic change
relative to `25daf34d`. `SHA256SUMS` covers the report, source overlays, paired
captures, state analysis and retained supervision data. Phase 5 remains open.

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

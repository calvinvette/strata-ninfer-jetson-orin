# Coder adaptive migration trace and CPU Q8_1 mirrors — Orin — 2026-10-20

This experiment used the current Orin candidate and the pinned **IQ1_M** Coder
GGUF artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
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
of the later layer-26 difference for this position. A paired follow-up also
found the shared-expert vector and combined MoE output bit-identical. The
remaining boundary is after layer-25 MoE combine: residual/
hyper-connection application or the following recurrent state transition. This
is still a single-position correctness trace, not a fix or a performance result.

The new capture built on Orin, and four focused CTests passed. Its supervised
same-service run passed with 14.31 GiB minimum host/admission availability,
10.85 GiB maximum scope use, and zero cgroup events; duration was 184.9 s.
Clocks were dynamic, EMC readback was denied, and energy was not request-
attributed. Raw files and the analyzer output are under
`layer25-verifier-parts/`; the focused report documents the reproduction
command and graph-capture position-filter behavior. A current top-level
verifier HIP rebuild on maestro1 recompiled the changed file and passed its
help check; the SYCL overlay was unaffected and its build reported no work.
These are compile/CLI checks only. A subsequent HIP rebuild covered the shared/
combined output diagnostic. The paired capture and analysis are in
`layer25-verifier-output-followup/`. A layer-26 GDN trace then showed that all
captured per-token inputs match, while the first differing value is the
state-dependent recurrent output `y`. The follow-up verifier-state snapshot
found that the recurrent matrix already differed before layer 26 processed the
recovery token (688,243/786,432 values); convolution history matched exactly.
This narrows the immediate boundary to the incoming recurrent matrix, but does
not identify which earlier token or operation introduced the difference. The
captured state belongs to the verifier diagnostic path, not the serving
session's accepted-prefix state. See `layer26-gdn-state-pair/` and
`layer25-to-layer26-gdn-followup/`. The GDN position-filter change also rebuilt
on maestro1 HIP; SYCL remains on its unaffected overlay. Phase 5 remains open.

A further opt-in trace captured layer-26 GDN state at every prefill chunk end
and wrote raw end-of-prompt state for the initial and recovery short requests.
The two 505-token internal prompt batches had identical full-state hashes at
boundaries 64, 128, 192, 256, 320, 384, 448 and 505. Their final FP32 states
were bit-identical across all 817,152 recurrent and convolution values. The
trace's low 16 bits also matched the existing per-layer prefill fingerprint on
both requests. At verifier position 511, however, the captured pre-verification
recurrent matrices differed in 688,243/786,432 values (maximum absolute delta
1.78e-4, relative L2 4.65e-4), while convolution history matched exactly.
This narrows the observed change to after the matching prefill snapshots and
before the verifier capture, but does not identify a specific token or
transition: the internal prefill batch ends at 505 while the verifier capture
is at absolute position 511, and these are different execution boundaries.
Cross-path raw arrays are retained as diagnostic data, not treated as
same-time state parity. The run passed its 28-GiB supervisor in 183.8 s, with
14.33 GiB minimum host/admission availability, 10.77 GiB peak scope use and
zero cgroup events. Clocks remained dynamic and energy was not request-
attributed. The capture and analysis are in
`layer26-gdn-prefill-state-comparison/`; raw state files remain outside Git
under `~/models/strata-orin-validation/experiments/phase5-gdn-state/`.

A follow-up `--spec 1` run intended to split that first two-token window was
rejected during native-pack argument validation (`--spec T` requires `T >= 2`);
it loaded no model and collected no state. The unsupported cell is retained in
`layer26-gdn-spec1-state-trace/`. Resolving the per-token transition requires a
capture inside the supported two-token window.
Phase 5 remains open.

The next accepted-state capture sampled layer 26 after every committed verifier
window through position 514. Initial and recovery token IDs match at all seven
captured endpoints. The earliest observed state difference is after the commit
ending at position 506: 786,389/786,432 recurrent values and 10,240/30,720
convolution-history values differ. At position 508 the convolution histories
are bit-identical again, but 786,367 recurrent values still differ. The
position-510 committed snapshots match the earlier position-511 verifier
pre-state snapshots byte-for-byte for both requests, validating the captured
state boundary. This narrows the first changed committed state to the verifier
window ending at 506 after identical prefill state at boundary 505; the capture
does not separate token-level work within that window. The same-service run
passed in 183.2 s with 14.31 GiB minimum host/admission availability, 10.90
GiB peak scope use, and zero cgroup events. The state records and analysis are
in `layer26-gdn-commit-state-trace/`; raw arrays remain outside Git under
`~/models/strata-orin-validation/experiments/phase5-gdn-state/`.

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
two jobs. The fresh SYCL build completed 123/123 steps using the refreshed
`sycl/src/program/generate.cpp` overlay. Exact source hashes, binary hashes and
logs are under `backend/maestro1-current-source-2026-10-20-iq3s/`; earlier
overlay diagnostics remain documented under the 2026-10-19 build report.
Maestro1 is x86_64, so these are build/CLI checks only. This change does not
alter default dispatch.
`source-overlay.patch` records the selector changes relative to source commit
`76eec469`; `gdn-state-capture.patch` records the state-dump diagnostic change
relative to `25daf34d`. `SHA256SUMS` covers the report, source overlays, paired
captures, state analysis and retained supervision data. Phase 5 remains open.

## Prompt-tail router and activation trace

The follow-up [two-position trace](layer26-gdn-prompt-tail-dispatch/README.md)
captures verifier dispatches at absolute prompt positions 505 and 506 in both
the initial 512-token request and its same-service recovery after the 2,048-token
request. Expert IDs match between requests through layer 26 at both positions.
Owner placement already differs at layer 1, but all 2,560 activation values
remain bit-identical through layer 25. Layer 26 is the first activation that
differs at both positions (relative L2 0.00482 at 505 and 0.00105 at 506).
Expert IDs first differ at layer 27 for position 505 and layer 31 for position
506. This localizes the first observed activation change but does not identify
the responsible upstream operation. “Coder GGUF” in the result name refers to
the two IQ1_M shards from the pinned repository revision above.

A randomized [delayed-control/adaptive pair](layer26-gdn-prompt-tail-dispatch/delayed-adaptive-pair/README.md)
then repeated the same positions with the same binary and model. Delayed
control had identical owners, expert IDs and activations across initial and
recovery requests; adaptive cap 8 reproduced the layer-1 owner, layer-26
activation and layer-27/31 expert-ID divergence. Both supervised services
passed with 14.27 and 14.19 GiB minimum availability and zero cgroup events.
The adaptive run again returned matching token IDs while its persistent-state
fingerprints differed. This associates the captured change with the tested
adaptive configuration, but does not isolate its underlying operation.

A follow-up [full GDN state comparison at accepted position 506](layer26-gdn-prompt-tail-dispatch/commit-state-pair/README.md)
shows that delayed initial and recovery states are bit-identical, and the
delayed initial state also matches adaptive initial. Adaptive recovery differs
from that shared initial state in 786,389/786,432 recurrent values and
10,240/30,720 convolution-history values. This confirms the adaptive-only
endpoint divergence without identifying the operation that introduced it.

A wider [positions 500–506 request](layer26-gdn-prompt-tail-dispatch/window-500-506-pair/README.md)
was accepted by the harness, but the runtime trace still emitted only verifier
positions 505 and 506. Positions 500–504 remain unsupported at this capture
boundary; the matching 505/506 results reproduced byte-for-byte.

An attempted pre/post GDN state snapshot at those two positions was also
unsupported: they execute as a two-token verifier window, while the current
state hook snapshots only single-token calls. The service requests completed,
but the runner rejected the missing requested dump; see the retained
[unsupported capture cell](layer26-gdn-prompt-tail-dispatch/gdn-token-state-adaptive/README.md).

The multi-row [GDN intermediate trace](layer26-gdn-prompt-tail-dispatch/gdn-intermediate-adaptive/README.md)
then showed layer-26 input `x` already differs at position 505. At position 506,
`x` and `qkv` match but the convolved value `h` differs, consistent with
position 505's transition changing the recurrent convolution history carried
into the second row. The upstream origin of the position-505 input difference
remains unresolved.

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

## Layer-25 owner-transition follow-up

The [position-505/506 owner and output capture](layer25-owner-position505-506/README.md)
now directly joins the service's layer-25 dispatch inputs to the verifier's
expert rows and the same-input CPU/GPU operator oracle. Adaptive recovery moves
expert 183 (`IQ3_S` / `IQ4_NL`) from CPU to GPU with identical input, IDs and
router weights. Both outputs match their corresponding parity output bitwise,
but differ by 1.2575% relative L2; the combined MoE vector differs at position
505. Delayed control is bit-identical at both selected positions. This
identifies an owner-dependent operator difference on the observed adaptive
path; it does not qualify long-chain drift, quality, or performance. See
`layer25-owner-position505-506/operator-comparison.json` and the retained raw
captures for exact values and reproduction.

## IQ3_S/IQ4_NL mirror and generated-position-520 trace

An opt-in CPU Q8_1 arithmetic mirror for IQ3_S/IQ4_NL now reproduces the CUDA
expert-183 output bit-for-bit on the captured layer-25 input. This corrects the
earlier owner-output difference above for that specific captured row; it does
not establish that adaptive migration is generally safe. With
`STRATA_NATIVE_CPU_Q8_1_DOT=all`, the repeated position-505/506 pair has
bit-identical initial/recovery activations and combined layer-25 MoE output at
both positions. The accepted state still differs, and its first observed
token-level state divergence is later, at accepted position 520.

The supervised [position-520 pair](layer26-generated-position520/) captured all
48 per-layer MoE dispatch inputs, IDs and owners plus the layer-26 GDN verifier
intermediates for initial short request versus adaptive recovery. Both arms
returned the same 16 recovery token IDs as their initial short request. The
delayed control had identical dispatch activations/IDs/owners across those
requests and bit-identical layer-26 GDN fields. In adaptive recovery, owner
changes first appear at layers 2 and 3; layer 4 is the first captured
activation difference. By layer 26 the GDN input `x` differs (all 2,560 values;
relative L2 5.743%). This indicates the changed verifier input was already
present before the GDN layer, but the captures do not identify which earlier
state transition or operator first caused it. Adaptive final fingerprints
still differ in `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`; delayed
fingerprints match. Minimum host/admission availability was 14.24 GiB for
adaptive and 14.36 GiB for delayed, with zero sampled cgroup memory events.
The capture is a correctness-localization diagnostic, not a timing or quality
comparison.

The raw GDN captures are 345,032 bytes each and their hashes plus per-field
comparisons are in `layer26-generated-position520/*-gdn-comparison.json`.
`layer25-owner-comparison.json` contains the layer-by-layer dispatch comparison.
The paired campaign metadata records the model revision, IQ1_M shard hashes,
binary identity and supervision results. The code and harness diff from the
recorded repository head is retained in
`source-iq3s-iq2s-and-capture.patch`. Reproduce the pair with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --continuations 0 --capture-moe-positions 520 \
  --capture-verify-gdn-layer 26 --verify-gdn-positions 520 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/reproduction-position520
```

The three comparison JSON files can be regenerated with
`compare_layer25_owner_positions.py --run <campaign> --positions 520` and
`compare_layer26_gdn_intermediates.py --run <campaign>/<arm>/result --positions 520`.

The subsequent [layer-3 verifier capture](layer3-generated-position520/README.md)
isolated the first changed operator boundary. At position 520, expert 182
(`IQ2_S`/`IQ4_NL`) changes CPU→GPU with identical input, IDs and router
weights. Its two service outputs match the same-input independent parity
outputs exactly, but differ from each other by 0.2819% relative L2. It is the
only differing routed expert row at layer 3; the combined layer-3 MoE output
differs, and layer 4 is the first changed activation. The Q8_1 CPU mirror
reduces this expert's CPU/GPU discrepancy from 1.82% to 0.2819% but does not
eliminate it. CPU down-projection on the GPU-produced hidden Q8_1 activation
matches grouped CUDA exactly, while the post-SwiGLU hidden Q8_1 rows differ in
all 60 blocks. A separate unfused-path capture finds the pre-quantized hidden
floats already differ (relative L2 0.00100083, maximum absolute difference
0.00019974); the resulting GPU Q8_1 blocks match the default fused path
exactly. This localizes the remaining arithmetic mismatch to gate/up or
SwiGLU before hidden quantization and down projection. It still does not
identify the first persistent-state write or qualify adaptive migration.

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

### 64-token accepted-prefix follow-up

Extending generation from 16 to 64 tokens exposed a later adaptive state
divergence. Initial and recovery short outputs had identical token IDs in both
arms. Delayed-control state remained identical through all 64 accepted
prefixes, while adaptive state first differed at zero-based prefix 8 and
remained different through prefix 63; GDN ordinals 24–35 were the first
per-layer hashes to differ. This confirms that the earlier 16-token parity
checks did not qualify longer accepted chains. The all-layer position-511
capture still found equal initial/recovery activations, with owner changes in
23 layers, so it does not identify the state divergence's first operation.
Both 28-GiB supervisors passed with zero cgroup events and at least 14.14 GiB
minimum host/admission availability. Full records and reproduction commands are
in [the 64-token campaign](reproduction-q8-cuda-input-quantizer-long64/README.md).
This remains correctness evidence for one model/configuration; adaptive
migration is still opt-in and Phase 5 remains open.

A current-source rerun with binary `081212f0…` extended the same request pattern
to 64 generated tokens and compared accepted-prefix states directly. Delayed
control matched all initial/recovery short states and token IDs. Adaptive
recovery differed from its initial short request at 40/64 token IDs, first at
output index 23 (accepted position 534). Its state first differed at accepted
position 515 (prefix index 4), with GDN ordinals 13–35 changed; 60/64 recovery
states differed. Both 28-GiB supervisors passed with zero cgroup memory events
and minimum host/admission availability of 13.97/14.34 GiB. See the
[current-source report](adaptive-current-081212f0-long64/README.md) and its raw
accepted-prefix analysis. This is one current-binary diagnostic and does not
establish a general drift bound.

The follow-up [multi-position capture](adaptive-state-prefix8-capture/README.md)
then localized the first accepted-state mismatch to prefix 8, logged after
verifier position 519. The first changed GDN fingerprint is ordinal 24 (model
layer 32); at the same position, the first changed captured MoE input is layer
32, with relative L2 `1.4294e-5`, while its expert IDs still match and its owner
placement differs. Delayed control remains exact across the capture. Earlier
adaptive activation differences did not yet change committed-state hashes, so
this is a boundary localization rather than proof of cause. A verifier-level
[layer-31 capture](adaptive-state-prefix8-verifier-capture/README.md) then
found matching IDs and router weights but a changed contribution for owner-
migrated expert 22; the weighted combine changed before the layer-32 GDN input.
The [raw committed-state follow-up](adaptive-state-prefix8-committed-raw/README.md)
then confirmed that the accepted layer-32 recurrent matrix first differs at
position 519, while convolution history stays bit-identical. The raw snapshot's
per-layer hash matches the service log at that accepted prefix. This directly
confirms the state divergence and strongly implicates the preceding owner-
dependent layer-31 expert-22 arithmetic; it remains correctness evidence for
this one model/configuration.

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

The [layer-33 expert-57 operator diagnostic](adaptive-layer33-q8-mirror-diagnostic/README.md)
then captured all three request rows and found identical adaptive layer-33
input, route IDs and weights while expert 57 moved CPU-to-VRAM. The default
standalone CPU/CUDA expert outputs differed by 1.32% relative L2; the targeted
Q8_1 CPU selector made this isolated output bit-identical. Applying that
selector in the service did not restore adaptive GDN state: the raw layer-33
post-state still changed while its pre-state matched. The same-prompt requests
used `--prompt-cache 0`, so live-session and batch-slot reuse are disabled for
this experiment. The operator gap is closed for the captured activation, but
its relationship to the continuing service-state mismatch is not established.
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

The [CUDA-order Q8_1 producer follow-up](layer3-generated-position520/README.md#cuda-order-q8_1-activation-quantizer-follow-up)
refines that boundary. Using the grouped CUDA reduction and rounding for the
opt-in CPU Q8_1 producer made the captured IQ2_S gate/up rows and all hidden
Q8_1 blocks bit-identical. Three same-service adaptive/delayed pair campaigns
then matched all short-request recovery tokens and accepted-state fingerprints
in both arms; the detailed position-520 pair retained exact router, expert,
combined-MoE and GDN verifier comparisons. All six supervised runs passed.
This remains one model/workload correctness evidence, with the selector
opt-in, and makes no performance claim. The current-source 18-test Orin
selection and 163 Python integration tests passed, and current-source HIP and
SYCL builds/CLI checks are recorded in
[`backend/maestro1-current-q8quant-2026-10-19/`](backend/maestro1-current-q8quant-2026-10-19/README.md).

A later direct-division replay on this same layer-3 expert-182 activation
changed 408/1,920 reconstructed hidden floats but left its Q8_1 bytes and final
expert output unchanged; the packed result remained bit-identical to CUDA.
The parity helper's reciprocal-form float assertion failed, so this is a
diagnostic comparison rather than a passing parity test. Combined with the
layer-39 improvement and layer-31 regression under the same global expression,
it does not justify changing SwiGLU arithmetic generally. The source was
restored; see the [layer-3 replay](layer3-generated-position520/operator-checks/expert182-q8_1-mirror/direct-silu-division/README.md).

## Prompt-tail owner trace through layers 12 and 13

The [layer-12 owner follow-up](adaptive-layer1-3-4-6-8-9-10-11-combined-mirror-layer12-prompt-tail505-511-pair/README.md)
found IQ3_XXS/Q2_0 experts 73 and 141 migrating CPU-to-GPU. Their valid
same-input native-oracle rows match the service. Layer-12 recurrent state at
position 511 remains exact across adaptive initial/recovery despite `ffn_y`
intermediate differences at three selected positions. The [layer-12 mirror
follow-up](adaptive-layer1-3-4-6-8-9-10-11-12-mirror-layer13-prompt-tail505-511-pair/README.md)
makes captured layer-12 GDN intermediates and state exact, then reveals IQ2_S/Q2_0
expert 147 migrating at layer 13 for all seven selected positions. Its seven
single-row oracle joins also match the service. Recovery token IDs match in this
12-token run, while all accepted-prefix states differ. The [layer-13 mirror
follow-up](adaptive-layer1-3-4-6-8-9-10-11-12-13-mirror-layer14-prompt-tail505-511-pair/README.md)
makes the selected layer-14 MoE, GDN intermediates and raw state exact, but
adaptive recovery token IDs then differ at all 12 positions. The dispatch trace
shows an IQ2_S/IQ4_NL expert-250 owner flip at layer 15, position 505, which is
verified by a same-input single-row oracle joined to the service CPU/GPU rows.
The [layer-15 mirror follow-up](adaptive-layer1-3-4-6-8-9-10-11-12-13-15-mirror-layer16-prompt-tail505-511-pair/README.md)
then exposed 21 layer-16 owner rows across experts 118, 220, 39, and 30. All
same-input native oracle rows match the service. Layer-16 raw state at accepted
position 511 remains exact across recovery, while `ffn_y` changes and the first
captured activation difference moves to layer 17. The [layer-16 mirror
follow-up](adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-mirror-layer17-prompt-tail505-511-pair/README.md)
makes selected layer-16 state and layer-17 outputs exact. Recovery tokens then
match, but accepted-prefix state still differs from prefix 0; the first captured
activation difference moves to layer 20, where the dispatch trace shows
expert 221 changing owner at layer 19. The [layer-19 mirror follow-up](adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-mirror-layer20-21-prompt-tail505-511-pair/README.md)
validates expert 221 at four positions and makes layer-20 GDN intermediates,
raw state, and layer-21 MoE outputs exact. Accepted-prefix state still differs;
the next selected activation differences are at layers 25–28. The trace shows
expert 173 changing owner at layer 24 at positions 507 and 511, with same-input
oracles matching both service rows. The [layer-24 capture](adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-mirror-layer24-prompt-tail505-511-pair/README.md)
found its GDN input/state and next-layer boundary changed, but adaptive
initial/recovery dispatch already differed by layer 3, so it could not isolate
the layer-24 row. A second randomized [layer-24 repeat](adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer25-repeat2-pair/README.md)
reproduced that layer-3 first activation difference at all seven selected
positions and the 12/12 adaptive token and state mismatch; delayed control
remained exact. A cross-request adaptive-history effect is plausible but not
isolated. These findings remain narrow correctness diagnostics and do not
qualify adaptive state transactions.

The [layer-2 boundary capture](adaptive-layer1-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer2-boundary-pair/README.md)
then found an IQ2_S/IQ4_NL expert-62 CPU/GPU owner flip at all seven positions.
Its service row alone changed among the ten routed experts, and the combined
MoE output changed; layer-2 GDN first differed at `ffn_y`, while raw recurrent
and convolution state at accepted position 511 remained exact. This makes the
layer-2 owner-dependent row a concrete candidate for the layer-3 input shift,
but the exact adaptive rows still need a direct independent-oracle join. A
follow-up with the layer-2 mirror enabled made the selected layer-2 expert rows,
combined output, GDN fields and position-511 state exact. Full adaptive recovery
still differs, with the next captured activation at layer 6 for positions
506–511 and layer 27 for position 505. The [mirror result](adaptive-layer1-2-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer3-boundary-pair/README.md)
is a local boundary result only; the layer-5 transition is the next target.

With layer 2 mirrored, the [layer-5 capture](adaptive-layer1-2-3-4-6-8-9-10-11-12-13-15-16-19-24-mirror-layer5-boundary-pair/README.md)
found expert 26 changing CPU-to-GPU at positions 506–511 with matching inputs,
routes and weights. Its service row matched the corresponding independent
native CPU/GPU oracle exactly; the two oracle outputs differ by 1.4092% relative
L2. Layer-5 GDN first changed at `ffn_y` at those positions while raw state at
accepted position 511 stayed exact. The layer-5 selector follow-up is next;
adaptive recovery still differs at all 12 tokens and accepted states.

Adding the layer-5 rule made its selected rows, GDN fields, and position-511
raw state exact, and adaptive recovery token IDs then matched all 12 positions.
Accepted-state hashes still differ at every prefix. The [layer-5 mirror
result](adaptive-layer1-2-3-4-5-6-8-9-10-11-12-13-15-16-19-24-mirror-layer6-boundary-pair/README.md)
moves the earliest selected activation to layer 19 at positions 506–511 and
layer 27 at position 505. Expert 110 at layer 18 changes owner on the first
branch; its same-input standalone oracle is retained, but still needs a direct
service-row join.

The direct [layer-18 service capture](adaptive-layer1-2-3-4-5-6-8-9-10-11-12-13-15-16-18-19-24-layer18-owner-capture-pair/README.md)
confirmed IQ3_XXS/IQ4_NL expert 110 as the only changed routed row at positions
506–511. Its same-input oracle matches both service owner rows bit-for-bit, with
a 1.5597% CPU/GPU relative-L2 difference. Layer-18 GDN first changes at
`ffn_y`, while sampled raw state at position 511 remains exact. Tokens still
match all 12 positions; accepted-state hashes still differ at all prefixes.


## Request-history control: three short requests

The [short/short/short history control](adaptive-short-short-short-history-control/README.md) tests whether the intermediate long request is required. In a randomized same-service pair, adaptive accepted-state and GDN hashes first differed at prefix 4 between the initial and intermediate short requests. The intermediate and recovery requests matched state, GDN and token IDs exactly. Delayed control remained exact. The repeated short/long/short pair showed the same state-prefix pattern. Thus the long request is not necessary for this observed adaptive divergence; the source of the state difference remains unlocalized. At captured positions 505–511, activation inputs and expert IDs matched across initial/recovery, while adaptive owner placement differed. These are correctness diagnostics, not a migration fix or performance result.


The [generated-position follow-up](adaptive-short-short-short-generated-positions512-523/README.md) captured positions 512–522 across the same three short requests (position 523 had no following dispatch). Adaptive state first differed between the initial and intermediate request at accepted prefix 4, then matched between intermediate and recovery; delayed control stayed exact. The first selected initial-to-intermediate activation difference was layer 27 at generated position 512, with expert IDs equal and owners differing at layers 26 and 27. This is a candidate boundary for the next exact-row/state capture, not causal attribution.



The [position-515 layer-16/layer-17 follow-up](adaptive-short-short-short-layer16-owner-layer17-state-position515/README.md)
joined the CPU-to-VRAM owner change for expert 118 with layer-17 GDN state.
Layer-17 raw pre-state matched before position 515 and post-state differed;
the delayed control and the second-to-third adaptive transition stayed exact.
The first direct-oracle comparison used the default CPU arithmetic mode and
was not comparable to the service setting. A mode-matched rerun with
`STRATA_NATIVE_CPU_Q8_1_DOT=all` matched the actual CPU-pool row to relative L2
9.51e-10; the same-input CPU/GPU rows differed by 0.01352% for expert 118.
Expert 39, the other migrating row, was bit-identical across CPU/GPU oracle.
The weighted owner-transition estimate is 1.36e-5 L2 and comes from expert
118 alone. The verifier-parts buffer is the verifier's assembled per-expert
buffer after CPU rows are copied and GPU-hit rows are added; it is the
mixed-owner data consumed by weighted combine, not an independent CUDA oracle.
A later same-service [cross-check](adaptive-generated-position512-layer40-expert114-mirror-state-pair/README.md#verifier-parts-capture-semantics-cross-check)
matched direct CPU rows to that buffer within JSON serialization precision.
The layer-17 input/router weights already differ, so this validates selected
rows but does not isolate the downstream state change. Phase 5 remains open.


The [position-515 layer-4 follow-up](adaptive-short-short-short-layer4-owner-gdn-position515/README.md) then checked the earliest selected owner change: expert 153 moved CPU-to-VRAM with identical input, and the mode-matched CPU owner output matched the CUDA oracle bit-for-bit. Its weighted row delta was zero, and the separate CUDA verifier's layer-4 GDN intermediates and raw state were exact. This clears that row as a measured numerical difference in the captured cell, while keeping the verifier/owner execution paths distinct. Layer 16 remains the first selected owner transition with a measured CPU/GPU difference; its relationship to the later layer-17 state write is still not isolated.
The [layer-16 targeted-selector prefill trace](adaptive-layer16-q8-targeted-prefill-state/README.md)
compared the first actual prefill in fresh adaptive and delayed-control
services. Layer-17 GDN chunk hashes matched at boundaries 64–505, and the raw
end-of-prompt recurrent and convolution state matched across all 817,152 values
bit-for-bit. Later identical prompts reused cached work, so this does not
resolve same-service adaptive history divergence. An attempted positions
505–511 verifier-state capture retained unsupported hook coverage (only
position 511 was observed); the paired run stopped before its delayed-control
arm. Phase 5 remains open.


The [layer-30 selected-expert and layer-32 state capture](adaptive-layer8-13-16-24-28-29-30-q8-targeted-no-cache-layer32-state511/README.md)
joined experts 121 and 212 to their actual CPU-pool rows and independent
same-input oracles. CPU service rows match the CPU oracle bit-for-bit, and the
same-input oracle CPU/GPU outputs are also bit-identical. The assembled
verifier-parts row for request 3 does not match that oracle, but its exact
verifier activation was not captured, so this comparison is unresolved rather
than a parity failure. The layer-32 accepted-state trace still changes between adaptive
intermediate and recovery requests even though the position-511 pre-state
matches. Phase 5 remains open.


The corrected [all-layer verifier-input trace](adaptive-no-cache-verifier-input-all-layers-corrected/README.md) captured 48 layer inputs for each of three no-cache short requests. Adaptive first-to-intermediate input divergence began at layer 34; intermediate-to-recovery first diverged at layer 12. The direct [layer-12/layer-34 state follow-up](adaptive-no-cache-gdn-state-layers12-34/README.md) now confirms the pre/post raw state at both boundaries and matches each post-state hash to the service GDN hash. For each adaptive transition, pre-state matches and post-state changes at the corresponding layer; delayed control remains exact. This confirms that the state difference follows the already-divergent layer input, but does not identify why that input changed or prove a migrating expert caused it. The initial all-layer capture remains invalid because its diagnostic source offset was wrong. Phase 5 remains open.


The latest [layer-31 expert-155 follow-up](adaptive-layer11-27-31-mirror-layer32-state-pair/README.md)
joined the CPU/GPU owner migration to an independent same-input oracle. With
layers 11 and 27 already mirrored, layer-31 expert 155 (IQ3_XXS/IQ4_NL) changed
owner on the same activation and route. Its layer-specific Q8_1 mirror made the
service rows and combined layer-31 output bit-identical and restored the
captured layer-32 raw GDN state across three same-service requests. Adaptive
accepted-state fingerprints still differed at all 12 prefixes, and the first
captured activation change moved to layer 33; the delayed control stayed exact.
This narrows another local boundary but does not qualify adaptive migration or
performance.

A later [layer-33 expert-57 oracle and Q8_1 mirror](adaptive-layer33-q8-mirror-diagnostic/README.md)
closed the isolated CPU/CUDA operator difference for its captured activation,
but not the service-state mismatch. The corrected all-layer trace found first
activation differences at layer 34 then layer 12 in the baseline adaptive
transitions; with the layer-33 Q8_1 selector they moved to layer 33 then layer
32. The raw layer-33 state still changed after adaptive requests, while delayed
control was exact. This localizes the next diagnostic boundary without
establishing a cause. Phase 5 remains open.

A [combined tested Q8_1 mirror screen through layer 33](adaptive-combined-tested-q8-mirrors-layers1-33/README.md) exercised the prior same-input oracle-checked rules together. Delayed-control outputs, all 48 position-511 activations, and GDN hashes stayed exact. In adaptive-cap8 the first two requests had the same tokens and position-511 activations; exact layer-32 raw state and the targeted layer-33 expert/combined output also matched. Yet accepted GDN hashes began differing at generated prefix 1, and recovery diverged from intermediate at the final six output tokens. Across intermediate-to-recovery at position 511, first changed activation was layer 33. This moves the next capture into generated positions; it does not establish that mirroring the selected prompt-tail rows fixes the accepted-prefix transaction. Phase 5 remains open.

A [generated-position 512 layer-26 owner trace](adaptive-generated-position512-layer26-expert213-mirror-state-pair/README.md)
then captured layer-26 expert 213 moving CPU-to-VRAM on identical input. Its
IQ2_S/IQ4_NL default CPU/CUDA oracle outputs differed by 1.49% relative L2;
the targeted Q8_1 path matched bitwise and its service CPU row matched the
oracle. Adding this rule made the layer-26 state exact through the first
adaptive transition and moved the first position-512 activation difference
from layer 27 to layer 41. The trace exposed layer-40 expert 114 (IQ3_S/IQ4_NL)
on identical input with an independent 1.33% CPU/CUDA delta; its Q8_1 oracle
matched bitwise. Recovery state still diverged, so layer 40 is the next
service-level mirror target and Phase 5 remains open. The all-layer 512–522
captures with the combined prior rules are documented in
[their generated-position report](adaptive-combined-tested-q8-mirrors-generated-positions512-522/README.md).

The [layer-40 expert-114 mirror pair](adaptive-generated-position512-layer40-expert114-mirror-state-pair/README.md)
then checked the next equal-input CPU-to-VRAM transition (IQ3_S/IQ4_NL). Its
same-input default CPU/CUDA delta was 1.33%; the targeted Q8_1 oracle matched
bitwise and the actual service CPU row matched the oracle within relative L2
1.69e-9. Adding this rule made layer-40 raw state exact through the first
adaptive transition and moved the first changed position-512 activation to
layer 42. The recovery transition still changes state, with accepted GDN hashes
different at every prefix despite matching 12 token IDs. Phase 5 remains open.

The [layer-41 expert-171 mirror pair](adaptive-generated-position512-layer41-expert171-mirror-state-pair/README.md)
then found another equal-input owner switch, this time IQ3_XXS/IQ4_NL at
position 512. Its default CPU/CUDA delta was 1.21%; the Q8_1 oracle matched
bitwise and the actual service row matched that oracle within relative L2
1.61e-9. With the rule enabled, all 48 captured initial/intermediate inputs at
position 512 matched, and raw layer-42 GDN state was exact across that
transition. The intermediate/recovery transition first diverged at layer 13;
accepted GDN hashes still differed at every initial/recovery prefix despite
matching 12 output tokens. Phase 5 remains open.

The [layer-41 expert-171 mirror](adaptive-generated-position512-layer41-expert171-mirror-state-pair/README.md)
then extended that boundary. The same-input CPU/CUDA difference was 1.21%
relative L2, while the targeted Q8_1 oracle was bit-identical and the service
CPU row matched within relative L2 1.61e-9. Initial/intermediate inputs at
position 512 and raw layer-42 state were exact; the next request-history
transition still first diverged at layer 13 and state hashes differed across
all initial/recovery prefixes despite identical token IDs. The [layer-12 raw
state follow-up](adaptive-generated-position512-layer12-state-after-layer41-mirror-pair/README.md)
is sampling that earlier boundary.

The [layer-12 raw-state and verifier-MoE capture](adaptive-generated-position512-layer12-state-after-layer41-mirror-pair/README.md)
then sampled the transition whose first changed input was layer 13. At position
512, all ten layer-12 expert parts, router IDs/weights, shared and combined
outputs were bit-identical, and raw layer-12 GDN pre/post state matched across
all three requests and to service hash ordinal 9. A later [layer-13 verifier,
GDN and raw-state capture](adaptive-generated-position512-layer13-gdn-state-and-input/README.md)
confirmed the layer-13 input, GDN intermediates and state were also exact. It
corrected an apparent activation delta from the CPU-pool trace: the recovery
row had no CPU-owned experts, so the host activation was stale. The first
changed authoritative verifier input on intermediate-to-recovery is layer 15.

The follow-up [position-512 layer-15 recapture](adaptive-generated-position512-layer15-gdn14-recapture-retry-countfix/README.md)
found the selected layer-14 inputs and raw state exact, with accepted-state
hashes differing only at prefixes 10–11. A multi-position [521/522 verifier
and QSA trace](adaptive-generated-positions512-521-522-layer14-state/README.md)
then found adaptive initial-to-intermediate inputs first differing at layers
40/41 and QSA state hashes at layers 43/47; delayed control remained exact.
Layer-39 IQ2_S/IQ4_NL owner changes are under a targeted Q8_1 mirror check.

A current-source [position-515 dispatch capture](adaptive-current-081212f0-position515/README.md)
reproduced the accepted-state mismatch. Adaptive recovery first diverged at
prefix 4 and GDN ordinal 13 (model layer 17); delayed control matched. The
first valid changed captured expert input was layer 18 (relative L2 0.0035630),
with matching layer-18 expert IDs and owners. Layer-17 host activation was
invalid in this capture. A follow-up [raw layer-17 verifier capture](adaptive-current-081212f0-layer17-position515/README.md)
found identical pre-state but an already-different `x` input (relative L2
`7.7344e-6`); the post-state then differed broadly. This localizes the change
before layer-17 recurrence, without identifying which upstream operation
changed `x`. Phase 5 remains open.

A current-binary [service CPU-output capture](adaptive-current-081212f0-layer16-service-cpu-output/README.md)
joins the same activation to actual service rows and independent CPU/CUDA
oracles. Experts 118 and 39 match their CPU oracle exactly; only expert 118
differs from its CUDA oracle (relative L2 `1.35199e-4`). Both experts change
from CPU to VRAM ownership on recovery. This identifies an owner-dependent
contributor for this sampled layer-17 state delta, while its complete
combined-output effect and general correction remain unqualified.

A [direct-division SwiGLU trial](adaptive-current-081212f0-layer17-position515/division-formula-trial/README.md)
on the same expert-118 activation left the CPU row and CUDA delta unchanged.
Independent stage checks retained exact gate/up dots and CPU down-projection
parity on CUDA hidden blocks, with 3/60 hidden-block scales differing. The
candidate failed the reciprocal-form independent reconstruction and was
rejected; the source and parity target were restored. This does not provide a
layer-16 correction.

The randomized [64-token layer-17 raw-state follow-up](adaptive-current-081212f0-layer17-common-prefix-samples/README.md)
confirmed this boundary over the longer recovery sequence. Adaptive per-GDN
hashes first differ at accepted position 515 (model layer 17), before the first
generated-token mismatch at position 534. The sampled layer-17 pre-state is
exact at position 515 but post-state differs in 785,280/786,432 recurrent
values and 10,232/30,720 convolution values; delayed control remains bit-
identical through all four sampled positions. This confirms the earlier
eight-token `x`-input localization without identifying the upstream operator.
The initial sample request for position 575 was correctly rejected as
uncaptured and is retained as a failed cell. Phase 5 remains open.

A current-binary [layer-16 to layer-17 boundary capture](adaptive-current-081212f0-layer16-to17-position515/README.md)
joins the adaptive state change to one changing expert row. At accepted
position 515, layer-16 input, token, expert IDs and router weights match across
initial/recovery. The shared output and nine expert rows match; only expert 118
changes, and the combined MoE output differs (relative L2 `2.50977e-5`). The
next layer's first changed GDN field is `x` (relative L2 `7.73436e-6`) with an
identical pre-state and changed post-state. A same-binary dispatch trace and
same-input oracle identify expert 118's CPU-to-VRAM owner transition and its
CPU/GPU arithmetic difference. Delayed control is exact. This strongly
identifies an owner-dependent contributor for this sample, without proving a
general correction; Phase 5 remains open.

The [layer-16 residual-boundary follow-up](adaptive-current-081212f0-layer16-boundary-position515/README.md)
recorded the transfer of that MoE delta. At position 515, adaptive post-layer
`bo` differs in 2,557/2,560 values, while residual `R` and `inj2` before the
next read stay exact. The subsequent `xn` changes in 8,898/10,240 values
(relative L2 `6.09090e-6`), followed by layer-17 GDN `x` and raw-state changes.
Delayed control remains exact in all captured fields. The analyzer was fixed to
handle two-record captures and rerun successfully; both service arms passed.
This strengthens localization for one transition but does not establish a
general correction or error bound. Phase 5 remains open.

The short-only [layer-27 owner transition and layer-28 state capture](adaptive-layer24-short-short-short-no-cache-layer27-state28-pair/README.md)
joins three repeated requests to an independent same-input expert oracle.
Adaptive layer 27 moves expert 175 from CPU to CUDA with unchanged activation,
expert IDs and router weights; each service row matches its owner-specific
oracle, and the combined MoE output changes. Delayed control remains exact.
The following layer-28 `x` input is the first changed intermediate, then the
accepted GDN state differs in adaptive mode, with raw hashes matching service
telemetry. The intermediate-to-recovery layer-28 trace is exact. This verifies
an owner-dependent contributor for the sampled transition but does not close
the full drift cause or bound. Phase 5 remains open.

A second [seed-20261079 reproducibility pair](adaptive-layer24-short-short-short-no-cache-layer27-state28-seed20261079-pair/README.md)
reproduced the seed-20261078 route, verifier input, expert parts, combined
output and layer-28 committed-state captures byte for byte. Since the prompts
and greedy outputs are fixed, this confirms reproducibility rather than adding
an independent randomized workload sample. Phase 5 remains open.

The [layer-27-to-33 owner-mirror chain](adaptive-layer27-33-q8-mirror-chain.md)
tested exact-input Q8_1 interventions at layers 27, 28, 29, 30 and 33. The
targeted rows match their CPU/CUDA oracles where the verifier input matches the
oracle activation, but no selector chain restored accepted-prefix state
equality. Some selector chains also changed recovery token IDs. The report
distinguishes two-row dispatch traces from three-request verifier captures; no
default changed. Phase 5 remains open.
The latest [fresh-source Q8_1 all-dot long-chain pair](adaptive-current-source-q8-all-long64-pair/README.md)
rebuilt the service from the current working tree and rechecked 64-token
accepted-prefix state across short/long/short recovery. Delayed control matched
all 64 prefixes; adaptive state first diverged at prefix 4 and differed at
60/64 prefixes, while recovery token IDs differed at 40/64 positions. Thus the
all-dot selector remains insufficient to bound migration drift. Both arms
passed memory supervision with at least 13.78 GiB host/admission availability.

The earlier layer-27–33 chain's 96-row dispatch capture was followed by a
[144-row, three-request recapture](adaptive-layer27-33-q8-mirror-all-three-dispatch-state28-pair/README.md).
It confirms identical initial-to-intermediate activations and expert IDs but
owner changes at ten layers; the next transition first changes activation at
layer 32. The third adaptive layer-33 verifier input is now explicitly
captured and does not match the oracle input. Adaptive accepted-state hashes
still differ at all 12 prefixes.

The [layer-11 expert-201 post-SwiGLU replay](operator-checks/layer11-position515/expert201/README.md)
further isolates its three changed Q8_1 code bytes: multiplying by a computed
sigmoid reproduces the CPU codes, while the CUDA direct-division expression
reproduces the captured GPU codes under both tested code quantizers. Both host
replays use `std::exp`, so this demonstrates the operation-order effect for
this row without claiming general equivalence to CUDA `__expf` or a fix for
accepted-state migration.

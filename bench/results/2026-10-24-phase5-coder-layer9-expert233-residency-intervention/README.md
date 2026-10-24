# Layer-9 expert-233 residency intervention

## Result

This single-pair Coder IQ1_M two-live diagnostic moved layer 9 / expert 233
from static residency rank 3,130 to rank 0 in a temporary profile. Both 72-token
batch outputs matched their isolated serial controls exactly. This changes the
previous two-live result, where slot 1 first differed at token 66.

At layer 9 / position 83 / input token 11, the serial and batch route IDs,
weights and 2,560-value activation were exact. Under the intervention expert
233 was GPU-owned in both paths; all ten expert parts and the combined MoE
output were bit-identical. The following layer-10 stage and committed state
were also exact for prompt 1 at that position. In the matching baseline capture,
expert 233 had moved GPU→CPU, its part differed on the identical activation,
the combined MoE output changed in 2,555/2,560 values (relative L2
`1.371e-5`), and layer-10 `x` changed. An independent native expert oracle was then run on the exact captured
activation and weights (IQ2_S gate/up, IQ4_NL down). It matched the serial
service part to the GPU output and the batch service part to the CPU output
bit-for-bit. The oracle CPU/GPU outputs differed in all 2,560 values (maximum
absolute delta `8.94e-6`, relative L2 `1.198e-4`; each was about 0.99% from the
float reference). This paired oracle supports owner-dependent arithmetic as
one cause of the sampled position-83 perturbation. The retained
`analyze_owner_oracle.py` checks exact routing, activation, service parts and
oracle outputs; its summary is `owner-oracle-analysis.json`.

The intervention does not establish multi-live state parity. At terminal
position 138 after 72 identical output tokens, direct GDN comparison found
prompt 0 first differed at model layer 5 and prompt 1 at layer 12. Prompt 1's
recurrent state at layer 10 was exact at that endpoint. Hash traces from the
72-token intervention run first diverged at batch position 75 / serial prefix
73 for prompt 0, and at batch position 89 / prefix 87 for prompt 1. The static
profile therefore restored output parity for this prompt pair while persistent
state still drifted. Other owner changes and recurrence arithmetic remain
possible contributors.

This is correctness evidence from one prompt pair, not an accepted-state
qualification, performance result, quality claim, or profile recommendation.
No default or shared model data changed.

## Resources and identity

The supervised terminal capture passed with minimum physical and admission
availability 17.72 GiB and zero sampled cgroup pressure events. The clocks were
observed dynamically; EMC readback was denied. Instrumented durations are not
performance measurements.

- Candidate binary SHA256:
  `1f44e7e3713faf9d1e1fee688a69ce5960e21d40c1d0d6071e9831dea53316d6`.
- Coder IQ1_M artifact revision: `5348543e0147355ac9cbcb031184a3546350988e`.
- Temporary profile SHA256:
  `41595f87b9947df82a492f4868e267013bf1fec8bae538f797a14e2b04ab64f4`.
- Model shards remain under `~/models/strata-orin-validation/`.

Compact retained evidence:

- `run/result.json`: output tokens, profile and artifact identity.
- `run/hash-analysis.json`: prompt-mapped per-prefix GDN hash comparison.
- `owner-oracle-analysis.json`: same-input service-to-CPU/GPU oracle pairing;
  `analyze_owner_oracle.py` is the reusable parser and checker.
- `run/moe-slot1.json`, `run/stage-slot1.json`: position-83 owner, part,
  output and stage comparisons.
- `terminal-position138/result.json` and `state-slot{0,1}.json`: direct terminal
  committed-state comparisons.
- Large raw state dumps, engine logs and supervisor telemetry remain local and
  are not included in Git.

The capture used `tools/integration/run_control.py` around
`bench/results/2026-10-23-phase5-coder-two-live-target-q8all/capture_position_state.py`
with `--position 83 --layer all --serial-slot both --generated-tokens 72
--expert-profile /tmp/strata-coder-layer9-expert233-first.bin --moe-layer 9
--stage-layer 10 --trace-state-hashes --trace-batch-gdn-hashes`. The profile was
generated with `make_expert_first_profile.py --layer 9 --expert 233`.

## Held-out prompt pair

The same rank-0 profile was checked on the next two prepared integration
prompts (65 and 66 prompt tokens), with 72 generated tokens per row. Both batch
outputs matched their isolated serial controls exactly. This is one held-out
correctness pair; it does not establish quality or general multi-live support.

The accepted-prefix state was not fully paired. At position 83, direct all-layer
state comparison was bit-identical for prompt 3, while prompt 2 first differed
at GDN layer 6. The per-prefix hash trace found the first mismatch for prompt 2
at batch position 75 / serial prefix 73 (18/36 allocations) and for prompt 3 at
batch position 86 / serial prefix 84 (7/36 allocations). For prompt 3 at layer
9 / position 83, expert 233 was not routed. For prompt 2, layer-9 route and
activation were already unpaired, so the sample cannot verify the intervention
there. The held-out pair therefore confirms output parity while also showing
persistent-state drift under the profile.

The supervised run passed with minimum physical/admission availability
17.745 GiB. Compact artifacts are under `heldout-pair-2-3/`: `result.json`,
`hash-analysis.json`, `state-batch0-prompt3.json`, and
`state-batch1-prompt2.json`; selected layer-9 analyses are retained as well.
Raw tensor dumps and telemetry remain local.

The rank-0 intervention repaired the original sampled output pair and also
returned exact output on one held-out pair, but neither pair had full terminal
state parity. Other state mismatches remain, and this does not qualify a profile
or close Phase 5. Multi-live committed-state behavior remains open.

## Operator-stage follow-up

The exact position-83 service activation was replayed through the independent
native expert parity harness with CUDA gate/up stages enabled. CPU-mirror and
CUDA Q8_1 input bytes matched, and all 1,920 gate plus 1,920 up values matched
bit-for-bit. After SwiGLU, 3 of 60 hidden Q8_1 blocks differed: blocks 4, 24
and 44 had a different fp16 `d` scale, while their stored sums and all integer
codes matched. The CPU IQ4_NL down operator fed CUDA's hidden Q8_1 blocks
reproduced the grouped CUDA output bit-for-bit. Thus this sample's CPU/GPU
output difference enters between the matching gate/up rows and hidden Q8_1
input to down projection. An opt-in reciprocal-SiLU CPU expression left the
same three blocks and output delta; the device exponential/rounding path is a
candidate for further investigation, not an established cause. This remains
one operator sample, not a state-parity qualification.

The parity harness now dumps the CUDA hidden f32 values when the separately
stored SwiGLU path is selected (`STRATA_GROUPED_V1=1`). On this activation the
default CPU quotient expression differs from CUDA in 258/1,920 hidden floats
(max `2.98e-8`); the reciprocal expression differs in 588 (max `5.96e-8`). An
offline host `exp2f(-g * log2(e))` quotient probe produced all 60 packed Q8_1
blocks exactly, while 264 hidden f32 values still differed. That host-libm
candidate is not CUDA `__expf`, and this one activation gives no basis to add a
serving option or infer cross-prompt parity. The retained
`analyze_silu_quantizer.py` and `silu-quantizer-analysis.json` record the
offline comparison. Raw stage files remain local.

The compact result is `operator-stage-analysis.json`. Large per-stage f32 and
Q8_1 dumps and the captured activation remain in `/tmp`; they are not Git
artifacts. Reproduction used the candidate `native_expert_parity` binary and
the environment/activation path recorded in the JSON.

## Held-out activation stage check

A second exact route/activation sample from the held-out prompt pair was
captured at layer 9, position 83, with expert 233 routed. The temporary profile
kept it GPU-owned in the service; we replayed that same activation through the
native CPU/GPU oracle rather than treating it as a CPU-owned service row. CPU
and GPU gate/up outputs, packed hidden Q8_1 (60/60 blocks), and final expert
output matched bit-for-bit. Their hidden f32 values differed in 234/1,920
positions (max absolute `2.98e-8`, relative L2 `4.08e-8`). Both host `libm`
`expf` and `exp2f(-g*log2(e))` candidates also produced the same packed hidden
Q8_1 bytes as CUDA on this sample; neither candidate is a serving change.

The first replay exposed a false failure in the parity utility: its independent
f32 reconstruction used reciprocal multiplication, while `native_gu_rows`
uses division before multiplying by `up`. The checker now mirrors that
operation order. The rebuilt CUDA utility passes on the original and held-out
activations; the corrected held-out reconstruction has zero
float mismatches. The original activation still shows three hidden scale-block
differences and an owner-output delta, while the held-out activation is exact
through packed hidden Q8_1 and final output. This supports sample-dependent
owner arithmetic, not general CPU/GPU parity. The HIP target compiled and
linked on maestro1 and its `strata --help` passed with the configured ROCm
library path; the HIP parity executable was not run because no HIP accelerator
was available there. The source is not in
the separate SYCL build. Compact hashes and build identity are in
`heldout-silu-activation-analysis.json`; raw activation and stage files remain
in `/tmp`.

## Seven-activation exp2f replay and opt-in service check

The follow-up sweep deduplicated seven captured layer-9/expert-233 Coder
activations and replayed each through the CPU/CUDA oracle. Gate and up values
matched bitwise for all seven. Default CPU SwiGLU produced the same hidden
Q8_1 blocks and final down output as CUDA on six of seven. The diagnostic host
`exp2f((-g)*log2(e))` candidate reproduced CUDA's packed hidden Q8_1 blocks and
CPU down output on all seven. This is a small captured-activation set, not a
general numerical guarantee. See `activation-rounding-sweep.json` and
`sweep_activation_rounding.py`.

An opt-in CPU selector was then added for a selected model layer and optional
expert ID: `STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_LAYER` and
`STRATA_NATIVE_CPU_Q8_1_EXP2F_SILU_EXPERT`. It only affects the native CPU
Q8_1 activation path and leaves defaults unchanged. A two-live 72-token
service replay was paired with a no-selector control using the same diagnostic
profile, with expert 233 at rank 12,287 (profile SHA-256
`1f03ed71cdac371e07480a3b4473e93be5cdfc9afb910f2fdac8491ac555502e`). Both
runs routed expert 233 to CPU in the batch row and GPU in serial at layer 9 /
position 83; the batch route IDs, weights and activation were identical. The
activation is the original seven-row sample `7ce8c948…d77b3`. Only the
exp2f selector changed. The captured CPU expert part changed in all 2,560
values (max absolute `8.94e-6`, relative L2 `1.198e-4`), matching the
independent owner-oracle delta. The selected CPU oracle returned zero failures:
all 60 hidden Q8_1 blocks and all 2,560 down-output values matched CUDA. The
captured service CPU expert part matched that selected CPU oracle bit-for-bit
(SHA-256 `cff8f354…f26061c`). The parity harness now reconstructs hidden f32
with the selected expression, so it does not misclassify the candidate as a
failure against the default `expf` path.

The no-selector batch output first differed from serial at token 66 for slot 1;
the exp2f batch output matched all 72 serial tokens. Slot 0's output stayed
unchanged. At position 83, slot 1's committed GDN state changed from first
differing at layer 10 in control to bit-identical with exp2f; slot 0 remained
first-different at layer 5. In accepted-prefix hashes, slot 1's first mismatch
moved from batch position 84 (28/36 GDN allocations) to position 89 (27/36);
slot 0 still first mismatched at position 75 (12/36). The candidate therefore
repairs this sampled output mismatch and delays, but does not eliminate, later
state drift. No default was changed; Phase 5 remains open. To reproduce, rebuild
`strata`, use
`capture_position_state.py --exp2f-silu-layer 9 --exp2f-silu-expert 233`
with the Coder settings from the run record, and place expert 233 outside the
initial GPU residency set. Omit these two variables for the paired control.
The prior rank-0 residency arm is a separate regression check, not the
same-profile control. The large `.stgcmt`,
`.stgdiag`, `.stmoe`, and `.stmparts` captures remain local and are not Git
artifacts. `exp2f-service-analysis.json` keeps compact source/profile/binary
hashes, route evidence, output comparisons, and accepted-prefix mismatch
locations. A reversed-order repeat (candidate before control) reproduced the
same exact route and activation, slot-1 token-66 baseline divergence, candidate
72-token match, position-83 state result, and 84→89 prefix-mismatch shift. This
is a repeat on the same prompt pair, not independent prompt confirmation. The
CUDA `native_expert_parity` and `strata` targets rebuilt. The Orin CTest
selector contract and synthetic IQ2_S/IQ4_NL Q8_1 dot/window tests passed 3/3.
HIP `strata` and
`native_expert_parity` targets built on maestro1; `strata --help` and the
selector-contract command passed with the ROCm library path. SYCL `strata` and
`native_expert_parity` compiled and linked on maestro1 after setting the
installed MKL 2026.1 `MKLROOT` and `LIBRARY_PATH`; `strata --help` could not run
because maestro1 has no SYCL device. No HIP or SYCL accelerator execution is
claimed.

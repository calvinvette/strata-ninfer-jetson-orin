# Layer-33 expert-57 operator and service-state diagnostic — Orin — 2026-10-20

This diagnostic tests whether one owner-dependent CPU/CUDA arithmetic difference
can explain the adaptive accepted-prefix state mismatch. It used the pinned
IQ1_M artifact from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, already stored under
`~/models/strata-orin-validation/`. Both service campaigns used candidate
binary SHA256 `e6209142c9df60ee8101b4c484e4f6d030d37d127d0447768de3af00b693171a`,
three identical 512-token requests, 12 generated-token limit, no prompt cache,
and supervised delayed-control/adaptive-cap8 pairs. The baseline retained 144
MoE rows so all three request rows were present for all 48 layers.

In the baseline adaptive transition from request 1 to request 2 at layer 33,
token 271, the activation, expert IDs and router weights matched exactly.
Expert 57 (IQ3_XXS gate/up, IQ4_NL down) moved CPU to VRAM. Its 2,560-element
output differed in every value (relative L2 1.3174%, maximum absolute
0.00227646); the shared output matched exactly, while the combined output had
relative L2 0.2107%. The corresponding delayed-control inputs and outputs were
exact. This makes the owner-dependent expert arithmetic a measured candidate
for that transition, not proof of the full state mismatch's origin.

An independent standalone oracle used the captured activation (SHA256
`ebe7af27cc296e2bfbc4e0ad086730f49f9d8284649c3f642c5e0553ecb7982a`). With
the default CPU path, all 7,680 output words differed from CUDA (relative L2
about 1.32%). Selecting the opt-in Q8_1 CPU dot path for
`iq3_xxs/iq4_nl@layer=33` made the targeted CPU and CUDA expert outputs
bit-identical; the gate/up reconstruction and Q8_1 blocks also matched. This
isolates and closes the standalone operator discrepancy for this input.

The same selector in a second service pair did not repair accepted state. Its
adaptive layer-33 inputs and router weights already differed between the first
two requests; raw layer-33 GDN pre-state matched, but post-state differed in
786,288 recurrent and 10,240 convolution values. In the next transition pre-
state again matched and post-state differed in 786,409 recurrent and 10,240
convolution values. Delayed controls remained exact in both pairs. The Q8
intervention also changed the generated-token sequence, so it is not evidence
that the state regression was solved. The targeted selector remains opt-in.

Comparing the retained all-layer position-511 activation trace shows where the
request-to-request activation boundary moved. In the baseline adaptive pair,
the first differing layer was 34 for initial-to-intermediate and 12 for
intermediate-to-recovery. With the layer-33 Q8_1 selector those first
differences were layer 33 and layer 32, respectively. Thus the selector
changes the path but does not make service activations or accepted state
consistent; the remaining divergence is already present before the targeted
layer-33 expert output is applied. Expert IDs first differ later (layer 36 on
the first Q8 transition, layer 43 on the second), so the earlier differences
are not explained by changed routing at those boundaries. This localizes the
next inspection but does not identify a specific upstream operation.

The runner uses one engine process for three fresh API requests. They all send
the same 512-token prompt, and `--prompt-cache 0` disables both live-session
resume and retained batch-slot conversation reuse. Thus a stale reused slot is
not supported as an explanation for these captures. Service state hashes were
cross-checked against each raw state dump. All four supervised arms passed;
the full campaign records, captures, comparisons, oracle output and commands
are retained alongside this report. These are correctness diagnostics, not
performance measurements. Phase 5 remains open.

Reproduction used `run_pair.py` with seeds `20261113` (baseline) and `20261114`
(Q8 mirror), `--sequence short-short-short --generated-tokens 12
--capture-moe-rows 144 --prompt-cache 0 --capture-verify-moe-layer 33
--verify-moe-positions 511 --verify-moe-input-layers all
--capture-verify-gdn-state-layer 33 --gdn-state-positions 511 --run`.
The Q8 campaign appended
`iq3_xxs/iq4_nl@layer=33` to the existing `--native-cpu-q8-1-dot` selectors.
The independent oracle was run with `native_expert_parity` on expert 57 and the
captured FP32 activation, first with its default mode and then with
`STRATA_NATIVE_CPU_Q8_1_DOT=iq3_xxs/iq4_nl@layer=33` plus hidden-Q8_1 parity
capture enabled.

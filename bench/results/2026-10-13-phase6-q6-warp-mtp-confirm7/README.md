# Q6 warp × MTP seven-block confirmation and accepted-state investigation

This Orin AGX campaign extends the 2026-10-12 three-block Q6_K warp-dequant ×
MTP screen with seven randomized paired blocks on a held-out 2,048-token
incident-log prompt, 128 generated tokens and 8K context. It used the current
IQ1_M Flash-Next pack, the same-day candidate binary recorded in each result,
3,903 cache slots, fresh services, default MTP batching, read-only clocks and a
28 GiB systemd scope. The six-GiB host headroom and separate 3 GiB workspace
reserve remained in force. Raw per-cell data, capabilities, logs, workload and
schedule are under `run/`.

All 28 cells (four conditions × seven blocks) passed request-length, fresh
prefill, cache-slot and resource gates. Within each fixed MTP regime, warp
dequantization improved median total request time by 7.253% with MTP disabled
(paired bootstrap 95% interval −7.951% to −5.783%) and 6.148% with MTP window 4
(−7.442% to −4.827%). The request interaction estimate was +1.148%
(−0.204% to +2.313%). Every baseline/warp output pair matched exactly at fixed
MTP. These are timing results for this prompt and hardware only.

The two MTP regimes did not produce the same generated output in any block:
their output SHA prefixes were `7b7cd547444e` (MTP off) and `ec417a6f0a71`
(window 4). Therefore the factorial timing comparison does not qualify a joint
MTP/warp profile or support changing defaults. MTP offered 153 drafts and
accepted 79 in each window-4 cell.

To localize the mismatch, a direct API harness captured published IDs and
accepted-prefix state for 32 tokens from the identical prompt with MTP off and
windows 2/3/4. The same harness was repeated with default batching after an
initial run with explicit batch size 1; the window-4 divergence reproduced
unchanged. The default-batch window sweep results are in
`run/incident-window-sweep/results.json`. MTP windows 2/3/4 first had unequal
state at shared committed prefixes 5/7/8 respectively, while all three first
changed a published token at index 13. The mismatching state fields included
GDN and KV, with other main-state hashes diverging as the request continued.
The no-MTP and window-4 GDN dumps at prompt+8 were numerically compared before
discarding the 113 MiB dumps: 94.443% of float elements differed, global
relative L2 was 0.01908 and global RMS absolute delta was 0.00514. This is a
material accepted-prefix discrepancy, not merely a hash-format difference.

The sweep ran under the 28 GiB scope and retained at least 13.41 GiB whole-host
availability; minimum effective availability was 9.94 GiB. No OOM event
occurred. EMC frequency was inaccessible; CPU/GPU rates were sampled without
changing clocks. Energy is not process-attributed. State tracing can perturb
runtime timing, so no timings are taken from that harness.

Two diagnostic controls narrow the failure. First, repeating off/window 4 with
`STRATA_GDN_COMMIT_SPLIT=0` (the ordinary multi-row GDN commit kernel) produced
the same first output mismatch at token index 13 and the same shared-prefix
state mismatch at prefix 8. Its GDN dump comparison also had exactly 27,782,662
different floats (94.443%), relative L2 0.01908 and RMS absolute delta 0.00514;
the first differing layer was layer 2. The optimized split commit kernel is
therefore not the sole cause. Second, a 512-token suffix of the same formatted prompt also
diverged: state first differed at shared prefix 5 and output IDs at index 10.
This argues against a failure unique to 2K prefill length, but the suffix is a
diagnostic token shape, not a standalone quality prompt. These results are
retained under `run/incident-state-unsplit-commit*` and
`run/incident-state-short-context*`.

The existing CUDA `gdn_parity --selftest` also passes: the multi-token GDN
recurrence is bitwise equal to repeated single-token recurrence in 84 synthetic
cases, and accepted-prefix convolution history matches in 44 cases. That
supports the kernel-level recurrence contract for its fixtures but does not
exercise activations from this production model's multi-token verification
path. The mismatch therefore still needs a live activation/intermediate-level
comparison; no numerical tolerance or code workaround is adopted yet.

This is a workload-specific Phase 5 correctness failure that reopens the MTP
accepted-prefix gate for the 2,048-token incident workload. It does not negate
the separately passing short-prompt or other long-prompt transaction tests.
Investigate verifier commit arithmetic/state replay before using MTP results as
quality-qualified Phase 6 candidates. Warp-dequant remains opt-in; no MTP
window or combined profile is promoted. No model, build output, credential or
113 MiB state dump is stored in Git.

To reproduce the seven-block timing screen, use `factorial_screen.py` with the
four saved configs and `schedule.json`; its outputs and analyzer result are
retained under `run/`. The direct trace commands are the Python harnesses
`compare_incident_state.py` (off/window 4, repeated with default batching) and
`compare_incident_windows.py` (off/windows 2/3/4). State-trace and supervisor
records are retained under `run/incident-state-*` and
`run/incident-window-sweep*`.

## Layer-input localization follow-up

The later layer-input capture repeats the exact 512-token suffix with the same
current engine, fixed 32-token generation limit, and fresh no-MTP/window-4
services. The accepted-prefix trace again first differs at generated prefix 5;
the output first differs at token index 10. Window 4 offered 42 drafts and
accepted 18. Both requests completed without OOM events under the 28-GiB
supervisor; minimum host and effective admission availability were 13.21 GiB.
The comparison is correctness-only because capture/state tracing synchronizes
GPU work.

At the selected GDN capture points, absolute layer 2 (the third model layer,
GDN ordinal 2) first differs at position 515/token 3766. Its pre-GDN mixed
activation differs in all 2,560 values (relative L2 0.002102, maximum absolute
delta 0.004664); QKV, convolution input, gate, beta, z, and recurrent output
also differ. Absolute layer 1 (the second model layer, GDN ordinal 1) remains
bitwise equal at shared captured positions through 519; its first difference
is at position 520/token 11040 (all 2,560 mixed-activation values, relative L2
0.002666, maximum absolute delta 0.006456). This brackets the first observed
activation discrepancy between the layer-1 GDN capture and layer-2 GDN input
for the shared row at position 515. The intervening residual/FFN operations
and MTP verifier-row arithmetic are not yet separated, so this is not a root
cause or a fix. No tolerance or alternate route is adopted.

The capture format is opt-in (`STRATA_VERIFY_DUMP_GDN_LAYER` plus
`STRATA_VERIFY_DUMP_GDN_PATH`) and records bounded verifier rows in a binary
`STGDIAG1` stream. `analyze_gdn_diag.py` compares the first two appended capture
streams by absolute position and token. State hashes, rather than the binary
state snapshot, remain authoritative for persistent state because the one-token
commit path can mutate convolution history before the snapshot. Large raw
float32 dumps were removed after extracting these compact metrics; logs and
supervisor telemetry remain. The new CUDA binary passed the focused 10-test
verifier/GDN/speculation/PLE/graph regression. On maestro1, the exact updated
`src/core/verify.cpp` and header were copied into the isolated validation tree.
The [maestro1 build record](MAESTRO1_DIAGNOSTIC_BUILD.md) lists their hashes and
scope. The HIP-configured Release build compiled the updated
`strata_engine/src/core/verify.cpp.o` (331,392 bytes); a focused Ninja target
recheck reported no work. The full HIP application build was stopped while
compiling unrelated llama.cpp MMQ kernels, before the `strata_engine` archive
and application link, so no full HIP build is claimed. The separate SYCL
`strata` target reported no work; its independent `sycl/src/core/verify.cpp`
and `sycl/include/strata/core/verify.hpp` were unchanged. Neither x86 check
claims accelerator runtime behavior.

As a follow-up control, the same suffix and output limit were repeated with
`STRATA_DEC_BATCH=0`. MTP still offered/accepted 42/18 drafts; accepted-prefix
state first differed at prefix 5 and token IDs at index 10, exactly as with the
default batch setting. The layer-1 capture likewise first differed at
position 520/token 11040 with the same x relative-L2 delta (0.002666) and max
absolute delta (0.006456). This rules out the broad decode-batching switch as
the sole trigger for this failure, though it does not isolate every operation
that still processes a verifier window. The supervisor recorded 13.24 GiB
minimum host/effective availability and zero OOM kills. The run is
correctness-only; its retained results and telemetry are under
`run/incident-no-decode-batch*`.

# Quick status

Updated: 2026-10-31

An opt-in Nsight graph-node diagnostic showed NInfer D3/D4 plus SwiGLU kernels account for 0.95% of the GPU-active interval union in the captured pp512 request pair; event overlap was only 0.35%. This is not a request wall-time fraction or a general speedup ceiling. Wait-flag, dequantization and other work remains. [Report](../../bench/results/2026-10-31-e6-q2-ninfer-kernel-share-diagnostic/README.md).

A new three-pair 5K adaptive-cache NIMBUS screen reached 76.0% GPU expert hits after warmup in both backends, yet NInfer decode TPS was 1.08% lower at the paired median; all measured outputs matched. No 5% gain or follow-up confirmation. [Report](../../bench/results/2026-10-31-e6-q2-ninfer-adaptive-5k-screen/README.md).

A correctness-only adaptive-state pair matched Strata and NInfer final fingerprints at both request ordinals. But identical warmup and measured prompts produced different state hashes and text by ordinal in both backends, so shared request-history variation remains open. [State record](../../bench/results/2026-10-31-e6-q2-ninfer-adaptive-5k-screen/state-parity.json).

Corrected reset/prefill checkpoints match through position 384; first sampled repeated-request divergence appears at prompt boundary 511, after 684 adaptive exchanges. Both backends still match at each ordinal. Exact slot-level cause remains unproven. [Boundary capture](../../bench/results/2026-10-31-e6-q2-ninfer-adaptive-5k-screen/boundary-capture.json).

A fixed-map follow-up ranked 5K resident experts from the workload's own route trace (85.23% trace coverage) and disabled adaptation. NInfer decode TPS was +1.19% at the paired median (95% screen interval −0.25% to +2.50%); all outputs and the 84.9% hit rates matched. This oracle profile still shows no 5% effect and is not deployable. [Report](../../bench/results/2026-10-31-e6-q2-ninfer-fixed-route-5k-screen/README.md).

A separate one-pair, hash-instrumented check with that fixed map matched all final persistent-state fingerprints across both backends and both same-process requests. Bounded final-state evidence only; no accepted-prefix or byte-level claim. [State record](../../bench/results/2026-10-31-e6-q2-ninfer-fixed-route-5k-screen/state-parity.json).

A three-pair 2K-prompt/128-cap comparison at a fixed 4K cache also found no NInfer decode gain: paired median 0.00% (95% screening interval −2.47% to +1.15%). Exact retrieval and arithmetic outputs matched. [Report](../../bench/results/2026-10-31-e6-q2-ninfer-backend-4k-pp2048-tg128-screen/README.md).

A same-profile 4K-cache pp512+tg128 backend screen found no NInfer request-level gain on NIMBUS: paired medians were −1.3% prompt TPS and −1.3% decode TPS, with TTFT/client time also about 1.2% slower. All six exact-answer responses matched byte-for-byte; no metric met the 5% screen. [Report](../../bench/results/2026-10-31-e6-q2-ninfer-backend-4k-tg128-screen/README.md).

An opt-in exact-entry-count Q2_0 kernel specialization passed parity and improved
grouped operator latency 11–12%, but the pp512 and pp2048 API screens showed no
useful end-to-end gain; ORBIT regressed. It stays experimental and is not a
service profile. [Report](../../bench/results/2026-10-31-e6-ninfer-q2-exact-entry-screen/README.md).

A Strata-only 3K/4K cache ablation reproduced higher decode TPS at 4K
(+16.9% NIMBUS, +20.8% ORBIT medians) with 11–13 point higher cache-hit
rates, but prompt TPS and TTFT regressed 8–10% and client total was tied.
Thus the decode gain is not unique to NInfer and this 4K profile fails the
combined latency gate. [Ablation](../../bench/results/2026-10-31-e6-q2-strata-cache-capacity-ablation/README.md).

A same-day 4K-cache, 8K-context NInfer-versus-Strata API screen measured
+3.33% median decode TPS at pp512+tg64, but its three-pair interval included
zero. Prompt TPS and TTFT were effectively tied, so no confirmation was run.
[Screen report](../../bench/results/2026-10-31-e6-q2-ninfer-backend-4k-api-screen/README.md).

A seven-pair held-out comparison found that 4K configured cache capacity with
default adaptive swaps improved decode TPS over 3K by 17.97% and 25.20% on two
Q2_0 retrieval tasks at 8K context (paired intervals +11.01% to +22.88% and
+23.13% to +28.28%). All 28 answers passed; minimum sampled available RAM was
10.25 GiB, with zero OOM kills. This is scoped to pp512+tg64 and does not
establish fixed residency or a general profile. NInfer-vs-Strata remains below
the 5% screen threshold. [Confirmation](../../bench/results/2026-10-31-e6-q2-cache-size-confirm/README.md).

A pp2048+tg48 3K/4K screen passed all six heldout retrieval/checksum responses,
but 4K decode TPS was 3.79% slower (three-pair interval −4.28% to −3.15%).
The earlier +18%/+25% decode result therefore applies only to pp512+tg64 so far;
adaptive swaps were active in both experiments. [Longer-prompt screen](../../bench/results/2026-10-31-e6-q2-cache-capacity-pp2048/README.md).

A seven-pair natural-stop confirmation at pp512+tg128 found +10.10% decode
TPS on NIMBUS (95% interval +9.91% to +10.53%) and +12.45% on ORBIT
(+4.83% to +15.97%). All 28 answers were exact at response start; measured GPU-cache hit rates
rose about 10 percentage points on both tasks. ORBIT naturally stopped at 117 tokens on 3K but hit the 128-token cap on 4K, so this
shows output-length/termination variation and not full-text equivalence. The
NIMBUS result has equal output lengths and prompt/TTFT median regressions under
5%. Adaptive swaps are active; this remains a scoped cache-policy result.
[Confirmation](../../bench/results/2026-10-31-e6-q2-cache-size-tg128-confirm/README.md).

Layer-1 expert-3 forced-owner repeats now match locally through layer 2 but
not across full GDN state: the second forced-CPU run differs from the first by
relative L2 `0.01078`, similar to forced versus adaptive. Keep that result
local-only. Repeated layer-5/7/13 owner interventions retain their bounded
causal state findings; none is a performance claim. [Layer-1 repeat](../../bench/results/2026-10-31-e6-q2-owner-intervention/layer1-full-state-repeat.md).

A Q2_0 NInfer grouped-kernel experiment tested 256-thread CTAs against the 128-thread default. It was numerically correct but 2.5–2.9% slower across measured operator sizes, so the default stays 128 threads and this variant is not qualified. [Operator report](../../bench/results/2026-10-31-e6-ninfer-q2-cta256-screen/README.md).

A same-day 4K-cache NInfer-versus-Strata pp512+tg64 screen found +3.33% median decode TPS, but the three-pair interval includes zero; prompt rate and TTFT were tied. No confirmation is warranted. [Screen](../../bench/results/2026-10-31-e6-q2-ninfer-backend-4k-api-screen/README.md).

This is a short orientation to the integration. The [plan](PLAN.md) defines
phase gates; the detailed [status](STATUS.md) is the evidence record, and the
[measurement protocol](BENCHMARKS.md) defines how to interpret results. The
[porting notes](PORTING_NOTES.md) preserve lessons for repeating this work with
Strata and Splash.

Portability is current at source `d321286f`: maestro1 rebuilt HIP and SYCL
with one build job. HIP help and the host shared-memory test passed; SYCL
compiled and linked after loading oneMKL, but cannot start without an available
SYCL device. This is x86 build evidence only. Scratch has space despite the
nearly full root filesystem. [Build record](../../bench/results/2026-10-30-e7-maestro-current-source-builds/README.md#2026-10-30-follow-up-request-tagged-route-trace-change).

The latest adaptive-history diagnostic found different 8K persistent state
after a 65K request despite the same first generated token. Disabling adaptive
residency restored the standalone 8K state under the same profile and prompt,
implicating request-time adaptation. A second adaptive run without route
capture reproduced the state and outputs exactly. An opt-in request-tagged
trace then captured the long→prefix replay's layer-1 row at position 8191 with
the same routed experts and owner kinds as the short repeated-position
control. The route row is now observable, but the specific transfer and
arithmetic cause remain unresolved. A matched fixed-owner accepted-prefix
trace found matching state after commit 1, then different GDN/tail/pooled/KV
hashes at commit 8 despite identical tokens; the round-4 adaptive update had
applied by then. Fixed-owner replay matched standalone state, while adaptive
replay retained its divergence. A boundary-only direct GDN byte dump confirmed
the replay state differs first at GDN allocation index 3; 33 of 36 allocations
differ, while the first three match. This localizes the state change without
identifying its causal transfer or operator. State-hash runs are too slow for
performance measurement, and a combined accepted-prefix/per-layer trace hit
the no-progress watchdog. The fixed-GPU no-trace screen remains effectively tied
(-0.46% prefill, 0.00% decode median for NInfer), with no ≥5% win. E6/E7 are
still open. [Diagnostic](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/adaptive-long-prefix-state-diagnostic.md).

A matched layer-0 trace across the same seven decode positions found identical
routes, owners and MoE inputs for fixed versus adaptive residency. The sampled
layer-1 expert-3 GPU→CPU eviction causes a tiny service-output delta; layer 2
receives a small activation delta. An all-47-layer bundle at position 65,540
then found larger drift by layer 13 (combined-output relative L2 `5.47e-3`),
with route IDs matching through layer 16 and first differing at layer 17. Same
output tokens do not establish accepted-state parity. Layer-13 experts 474,
385 and 250 moved CPU→GPU, and the independent oracle confirms the same-input
CPU/GPU gap is only about `1.1e-7`; their larger output delta follows the
changed activation. Layer-13 GDN capture shows identical projected qkv, then
recurrent output `h` differs by `2.52e-5` relative L2 and committed state differs
by `2.35e-5`; locating whether that state is already different on entry is the
next check. E6/E7 remain open. [All-layer comparison](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/all-layer-position65540-comparison.json),
[owner oracle](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/active-owner-oracle-position65540.json),
and [GDN stages](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/gdn-layer13-position65540-comparison.json).

The fixed-GPU resident-backend screen now has three no-trace pairs: median
NInfer changes were -0.46% prefill and 0.00% decode, below the 5% screen. One
Strata decode arm was an unexplained 0.9 tok/s outlier; the opposite-order
repeat tied at 4.1 tok/s. No seven-pair confirmation is indicated for this
fixed-owner path. See the [screen report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/fixed-gpu-resident-backend-screen.md).

## Overall status

Phases 0–8 are complete for the bounded Orin and backend scopes documented in
their closeouts. Phase 5 supports tested single-live static-routing transaction
and graph behavior; adaptive CPU/GPU migration and multi-live batch decoding are
excluded because accepted-state/output parity fails. Phase 6 records randomized
screens and held-out confirmations for specific factor/workload cells; no
global Pareto winner or default is promoted. Phase 8 releases one opt-in Q2_0,
FP16-KV, MTP-off profile. See [Phase 5](PHASE5_CLOSEOUT.md),
[Phase 6](PHASE6_CLOSEOUT.md), and [Phase 8](PHASE8_CLOSEOUT.md).

The current Orin CUDA functional suite registered 135 cases: 132 passed, two
optional IQ fixture cases skipped, and the default `pool_test` fixture was
missing; the same test passed when supplied with the existing external Q2_0
fixture. The GDN verifier convolution parity extension passed T=1..8 and every
split offset. maestro1 rebuilt five current shared C++ files for HIP and SYCL at
one job; the HIP host memory-budget test and both service help checks passed.
The current SYCL runtime had no device, and maestro1 provides no accelerator
execution evidence. See the [CTest report](../../bench/results/2026-10-24-orin-cuda-functional-ctest/README.md) and [backend report](../../bench/results/2026-10-24-phase8-maestro1-incremental-current-shared-build/README.md).

Older dated entries below preserve the evidence and phase state at the time each
experiment was recorded. Models stay in `~/models/`; generated builds,
telemetry and raw captures are not committed.

The NInfer expert integration itself remains experimental: E6 correctness,
quality, context, and performance gates are still open, and E7 proposes no
general release profile. New no-staging 3-pair API screens found no qualifying
benefit at pp512+tg64 (median +1.16% decode TPS, +0.84% client time) or
pp2048+tg128 (median tied decode TPS, -2.34% client time); the latter had one
unrepeated decode outlier. Both matched content within pairs but lacked an
independent task-quality oracle. A separate 2K held-out retrieval check passed
exact answer, token, persistent-state, and residency gates for both backends.
Two additional three-pair capacity screens at 2K and 8K with pp512+tg64 also passed. Median NInfer effects were +1.31% prompt TPS, -0.04% decode, -1.22% first-visible TTFT, and -0.83% client time at 2K; at 8K they were -0.48%, -0.78%, +0.42%, and +0.94%. None reached the 5% useful-effect screen. All six requests in each cell matched output within pairs. [Reports and paired data](../../bench/results/2026-10-31-e6-q2-2k-capacity-api-screen/README.md).

An added three-pair no-trace screen at 256K configured capacity with pp512+tg64
also found near-zero effects: -0.23% prompt TPS, -0.68% decode TPS, +0.27%
first-visible TTFT, and +0.33% client time; every interval crossed zero and
all six requests remained above the six-GiB floor. The combined figure now
includes this cell. A matching 128K-capacity screen found +0.29% prompt TPS,
-2.92% decode TPS, -0.27% TTFT and +0.56% client time, again with every
interval crossing zero and no memory-floor breach. Both use short prompts;
neither is near-limit ingestion or a quality oracle.
The follow-up 256K exact retrieval check also passed: one 256,000-token
Strata/strict-NInfer pair matched the exact answer, all 47 tokens, nine final
state fingerprints and residency. NInfer's single-pair rates were only +0.10%
prompt and +1.98% decode over Strata; this is functional coverage, not
performance confirmation. Minimum available RAM stayed above the six-GiB floor
(6.56 GiB in the full sample series). See the [256K report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/quality-retrieval-256k-README.md).
The latest 65K repeat localized the expert-row/output change to a cache-owner
transition: expert 320 was CPU-served on request 1 and GPU-resident on request
2. Exact-input CPU/GPU replay matched each service row; with cache adaptation
disabled and the expert kept CPU-owned, both repeated requests matched all
captured state and MoE bytes. This explains the observed request-order change
for that expert, while showing that NInfer covers only GPU-resident work. It
does not establish an end-to-end speedup. A fixed-GPU-owner same-process
control now also matches prompt-boundary/final state and the full captured MoE
bundle across repeated requests. Both CPU and GPU fixed-owner controls pass
for the sampled boundary. Both owner modes also matched their 32 output token
IDs and all eleven state fingerprints at five sampled accepted prefixes across
repeated requests. Cross-owner state already differs at the prompt boundary,
and sampled tokens split at checkpoint three. E6/E7 still need broader
quality/repeatability and no-trace performance qualification. See the
[ownership report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/layer1-moe-expert320-transition.md).
A no-trace fixed-GPU resident-backend pilot then compared Strata with strict
NInfer on the same 65K prompt/profile. Both arms emitted identical token IDs
and recorded 12.2% GPU-cache hits. NInfer was 0.46% slower on prompt rate and
4.88% slower on decode in this single pair. Two more screen pairs remain; this
is not a performance qualification. [Pilot report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/fixed-gpu-resident-backend-ablation-pilot.md).
The new 16K no-trace API screen also found no qualifying effect: median changes
were -0.12% prompt TPS, 0.00% decode TPS, +0.19% TTFT and +0.18% total time
across three pairs; all bootstrap intervals included zero. All pairs ran
NInfer first and did not collect semantic/state evidence. Its [report and
paired-effect chart](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp16384-cap32768-README.md)
join the existing 1K/4K screens.
The 32K prompt/64K capacity no-trace API screen was also flat: median changes
were +0.12% prompt TPS, -1.12% decode TPS, -0.07% TTFT and +0.01% total time
across three mixed-order pairs; all intervals included zero. Minimum available
RAM was 9.95 GiB. The generic workload did not collect state or provide an
answer oracle. See the [32K report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp32768-cap65536-README.md)
and combined paired-effect chart.
The 64K prompt/131K capacity screen was also below the 5% threshold: median
changes were -0.20% prompt TPS, +3.16% decode TPS, +0.25% TTFT and +0.86%
client time. All intervals included zero, and one decode outlier made the
interval wide. With explicitly greedy sampling (temperature 0), warmups
matched but measured output text differed in all three pairs; five of six
same-process repeats also changed. This flags an unresolved repeatability/state
issue, and decode/total-time effects are confounded by different generated
paths. Minimum available RAM was 7.12 GiB; peak sampled swap was 6.33 GiB. See the [64K
report and combined chart](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/no-trace-api-pp65536-cap131072-README.md).
The accepted-prefix follow-up matched all 32 token IDs and state fingerprints
across ports under heavy tracing, but it did not reproduce the no-trace output
divergence. NInfer's first measured state hashes changed after different
warmup history even though its first token stayed the same. The tracing run took
about 76 minutes per arm, so the result is correctness-only and may perturb the
path. Next use buffered or sampled checkpoints and verify no-trace output
preservation. See the [diagnostic report](../../bench/results/2026-10-29-e6-q2-state-repeatability-length-screen/accepted-prefix-instrumentation-README.md).
See the [integration status](STATUS.md) and
[latest E7 assessment](NINFER_E7_RELEASE_ASSESSMENT.md).

## Performance observed

The requested dense Qwen3.8-27B UD-IQ3_S GGUF is unsupported by the current
Strata candidate: its header declares `qwen35`, while Strata accepts only
Flash-Next. No timing requests were run. NInfer's available dense-model `.ninfer`
artifacts are a different format and cohort. [Support check](../../bench/results/2026-10-25-dense-iq3s-support-check/README.md).

The qualified Q2_0 profile was clean-rebuilt on 2026-10-25 from the current
runtime source; its executable hash matched the preceding current-candidate
build. Seven process blocks measured 32.6/10.2 prompt/decode tok/s at 512/64
and 54.2/10.4 tok/s at 2,048/128. Median client TTFT/request times were
15.88/22.00 s and 37.97/50.10 s. All requests passed token-count checks;
minimum physical/admission availability was 17.74/7.36 GiB, with zero cgroup
memory events. This is performance evidence for the bounded profile, not a
quality result or a paired quantization comparison. [Full report](../../bench/results/2026-10-25-q2-current-candidate-performance/README.md).

A seven-block current-candidate run on the Coder IQ1_M shards measured 65.2
prompt / 16.0 generated tok/s at 512/64 and 68.5 / 15.9 tok/s at 2,048/128.
Median client TTFT was 7.93/29.97 s; median full request time was 11.85/37.97
s. Seven independent process blocks passed exact token-count checks. The
3,000-slot request realized 3,903 slots; minimum physical/admission availability
was 14.18/9.69 GiB, with zero cgroup memory events. Energy was not measured.
This is a separate Coder IQ1_M cohort, not a paired quantization comparison or
a change to the bounded Q2_0 release profile. [Full report](../../bench/results/2026-10-24-coder-iq1m-current-candidate-performance/README.md).

A seven-block current-candidate run on the original Qwen3.8-Flash-Next IQ3_S
model measured 13.1 prompt / 5.7 generated tok/s at 512/64 and 22.1 / 6.3
tok/s at 2,048/128. Median client TTFT was 40.06/93.46 s; median full request
time was 50.82/112.93 s. The 3,000-slot cache request realized 3,904 slots
(7.44 GiB). Minimum host availability was 12.77 GiB and minimum admission
availability 10.07 GiB; cgroup memory events stayed zero. Host-wide NVMe reads
were high at 33.81/50.08 GB per request and are not process-attributed. This is
an exploratory IQ3_S cohort with dynamic MAXN clocks, no paired Q2_0 control, and
no output-quality oracle; it does not widen the bounded Q2_0 release profile.
[Full report](../../bench/results/2026-10-24-iq3s-current-candidate-performance/README.md).

A current Phase 5 two-live diagnostic found a local owner-dependent change at
Coder layer 9 / expert 233. Promoting that expert to GPU residency restored
exact 72-token output parity on the original prompt pair and one held-out pair,
but direct terminal GDN state still differed at layers 5 and 12; another held-out
prompt already differed at layer 6. This temporary profile is not qualified and
no default changed. [Intervention evidence](../../bench/results/2026-10-24-phase5-coder-layer9-expert233-residency-intervention/README.md).
On a second held-out layer-9/expert-233 activation, native CPU/GPU gate/up,
hidden Q8_1 and expert outputs were exact; the earlier owner's output delta
therefore depends on activation. This also exposed and fixed an operation-order
false failure in the native parity utility; the rebuilt CUDA utility passes
both replays, and its HIP target compiled/linked on maestro1. This remains
narrow diagnostic evidence, not broad owner parity.

A seven-block held-out 7,501-token confirmation passed all 28 MTP-off/MTP3 ×
FP16/INT8 KV arms. MTP3 reduced decode throughput 5.49% (FP16) and 4.19%
(INT8), while total request time rose 0.67% and 0.89%. The named-rail follow-up
found higher CPU/CV energy/token and small lower GPU/SOC energy/token; system
rail intervals included zero. The response model has residual outliers, so the
paired bootstrap is primary. No default changes. [Report](../../bench/results/2026-10-24-phase6-coder-mtp3-kv-heldout-long-confirm7/README.md).

A seven-block held-out Coder IQ1_M worker × transfer confirmation passed all 28
cells with identical output hashes and 3,903 actual cache slots. Four workers
were slower than eight by median 7.36% mapped and 6.50% `pread`; `pread` was
faster by 2.72% at four workers and 1.94% at eight. The worker × transfer
interaction interval included zero. One 8-worker/mapped decode-time outlier is
retained and documented. Minimum physical/admission availability was
13.99/9.60 GiB with zero cgroup events. No setting changed; this is one bounded
workload result. Retrospective named-rail integration found a small system-rail
energy/token decrease for `pread` at four workers, while CPU/CV rail energy
increased; rails include background load and are not summed. [Confirmation](../../bench/results/2026-10-24-phase6-coder-worker-transfer-confirm7/README.md),
[screen](../../bench/results/2026-10-24-phase6-coder-worker-transfer-screen3/README.md).

A current-source owner-transition diagnostic at layer 27 / generated position
515 found exact selected expert output and all-layer committed GDN state across
an adaptive CPU-to-CUDA owner change for expert 129. This is narrow correctness
evidence only; it does not close Phase 5 or establish broad owner parity. See
the [capture notes](../../bench/results/2026-10-22-phase5-coder-adaptive-all-layer-position-trace/adaptive-layer27-current-source-generated-position515/README.md).

A current-binary Coder IQ1_M adaptive/delayed pair reproduced cross-configuration
state divergence at accepted position 532; 64-token recovery stayed exact within
each service. A focused capture found CPU/GPU ownership differences before the
first changed MoE input activation (layer 36 at short position 532; layer 41 at
long position 2067), while all long-request output tokens still matched. This
is localization evidence, not a causal or performance result. Phase 5 remains
open. [Report](../../bench/results/2026-10-23-phase5-coder-adaptive-divergence-532-2067/README.md).

A supervised 72-token two-live target-only repeat matched slot 0's serial output
and first differed at slot 1 token 66. Four captured accepted-prefix states at
slot handoff matched serial exactly, but the remaining batched decode emitted
no prefix trace. A later full-state capture matched slot 0's 72 output tokens
but found a terminal GDN delta from layer 5 (whole-state relative L2
`2.24e-7`); a per-prefix hash scan found earlier divergence at batch position
75 for slot 0 and 84 for slot 1. Slot 1's terminal state was not paired after
its output diverged. A direct capture at slot 1 position 84 found layer 10
recurrent-state drift (`1.88e-7` relative L2), with `y` the first changed
stage field and later captured fields exact. The incoming state was already
different there; another run found drift at position 83, so the onset varies
between runs and its cause remains unresolved. These are correctness
localization results, not performance evidence. [Details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

These results are specific to the tested Orin build, model and workload. No
candidate setting has been promoted to a default.

| Experiment | Measured result | Scope |
| --- | --- | --- |
| Expert cache × context, Coder IQ1_M, held-out 7,501-token task, seven same-day blocks | 3,000 vs 1,500 requested expert-cache slots reduced median client latency 7.95% at 8K context (paired 95% interval 7.93%–15.11%) and 7.71% at 16K (7.23%–7.82%). Cache-by-context interaction was +1.12% (0.22%–8.58%). | MTP off, FP16 KV, exact 48-token answer; one long-task profile. [Report](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/README.md) |
| Expert cache, short Coder task, seven blocks | 3,000 vs 1,500 requested slots reduced median client latency 12.83%; TTFT fell 13.47%, with prompt/decode throughput up 15.77%/10.24%. | Short task only; see [STATUS](STATUS.md). |
| MTP × prompt length × KV, Coder IQ1_M, seven blocks / 56 arms | On the 7,501-token task, MTP4 reduced decode throughput 9.17% with FP16 KV and 9.24% with INT8; client time rose 0.59% and 1.01%. Short-task effects were smaller and uncertain. | MTP4 was dominated on measured long-task latency and named-rail energy; no default changed. Other Phase 6 factors remain open. [Report](../../bench/results/2026-10-21-phase6-coder-current-source-mtp-kv-short-long-confirm7/README.md) |
| Prefill chunk × expert cache, Q2_0 near-limit retrieval, seven held-out blocks | Chunk 128 reduced median request time 59.54% at 3,000 slots and 59.74% at 3,500 slots; all 28 requests returned the exact 41-token answer after 7,506 prompt tokens. | Cache × chunk interaction interval included zero; no general default. [Report](../../bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/README.md) |
| Named-rail energy for the same Q2_0 cache × prefill campaign | Chunk 128 lowered `VIN_SYS_5V0` median energy per total token 59.43% at 3,000 slots and 59.41% at 3,500; cache × prefill interaction interval included zero. | Retrospective request-window rail integration, includes idle/background activity; not process-attributed or whole-device energy. [Analysis](../../bench/results/2026-10-18-phase6-q2-cache-prefill-heldout-confirm7/rail-followup/README.md) |
| Coder two-live residency profile, three paired screening blocks | Moving layer-9 expert 233 to first rank restored exact 96-token output parity for both live rows on the original pair. Median paired batch throughput changed −1.40% (three-block bootstrap 95% interval −2.17% to +16.66%). | A held-out pair still diverged on slot 1 at token 78 under both base and candidate profiles. No performance promotion or general correctness claim. [Report](../../bench/results/2026-10-23-phase5-coder-layer9-expert233-residency-intervention/README.md) |

The four-cell descriptive Pareto view keeps all profiles nondominated across
latency, decode, observed host availability, named-rail energy, and logical
file reads. Higher cache and larger prefill chunk trade lower latency/energy
for slightly lower observed host availability; physical disk I/O is not
attributed. This does not promote a default.

A three-request same-engine MTP test required and observed three rejected
drafts in the middle request, then matched MTP-off output and all main-model
state fingerprints through a further recovery request. All shared accepted
prefix boundaries matched across the three requests for one 512-token Coder
prompt. This is narrow transaction evidence; long-chain adaptive drift and
multi-live state/output parity remain open. [Report](../../bench/results/2026-10-23-phase5-coder-mtp-rejection-recovery/README.md).

A near-limit 7,498-token Coder prompt extended this to a rejection in the
initial request followed by two same-engine continuations. MTP4 rejected 9/15
drafts; all shared state boundaries and all three outputs matched MTP-off.
This single prompt does not bound adaptive migration or multi-live decoding.
[Report](../../bench/results/2026-10-23-phase5-coder-mtp-long-rejection-recovery/README.md).

A short-prompt and a 7,501-token MTP3 follow-up both matched MTP-off outputs
and all shared main-model state fingerprints across three same-engine requests.
MTP3 rejected drafts before recovery in both cells; the near-limit run retained
13.283 GiB minimum physical/admission availability. These add two transaction
cases, not an adaptive-chain or multi-live bound.
[Short](../../bench/results/2026-10-23-phase5-coder-mtp3-rejection-recovery/README.md),
[near-limit](../../bench/results/2026-10-23-phase5-coder-mtp3-long-rejection-recovery/README.md).

The matching current-build accepted-window, GDN recurrent/parity and captured
graph CTests passed 5/5 under the 28 GiB supervisor, with 23.73 GiB minimum
host availability and no cgroup memory events.

The [batch-MTP graph lifecycle diagnostic](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md)
admitted eight slots and captured 16 layouts under the default 64-layout cap,
so that initial run did not exercise eviction. A separate opt-in cap-1 test
completed eight concurrent requests and observed 14 LRU evictions and 11
recaptures across four repeated layout keys; all requests returned six tokens,
with 16.50 GiB minimum available RAM and zero cgroup memory events. The default
cap remains 64, confirmed by a no-override run whose six-token single-request
output matched serial MTP2. A supervised 80-request stress exercised 88 unique
layouts: the first eviction came at layout 64, and 26 evictions occurred in
total. All requests completed, minimum host availability was 11.12 GiB, and
784 supervisor samples showed zero cgroup pressure or OOM events. This is
lifecycle and memory evidence only, not a correctness or speed result. Outputs
in the original eight-prompt batch differed from
serial controls; a same-profile single-live follow-up matched serial MTP2,
while a two-request run still diverges at token 60 on slot 1 for MTP-enabled
and MTP-disabled batches. Full state capture corrected the earlier layer-6
pairing: at positions 71–72, each batch slot is closest to its corresponding
isolated serial prompt, but state arrays differ broadly despite equal short
outputs. At position 127, all 248,320 verifier logits differ and the top-two
ranking reverses. Batch-MTP remains unqualified; no throughput claim is made.

A new position-76 MTP2 comparison pairs rows by generated token. Prompt 0's
committed GDN state differs from its serial control in 26,965,859/29,417,472
values (relative L2 0.01823), first at model layer 4, despite an identical
64-token output. Prompt 1 did not produce a captured commit at that position.
The batch QSA hash hook stopped at state length 69, so it cannot rule out an
earlier QSA difference. This narrows the observed state onset for one row but
does not explain the two-live output mismatch or pass Phase 5. See the [state
follow-up](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A 3,000-slot cache correctness diagnostic is now localized one layer
earlier: layer-10 experts 150 and 2 switch from VRAM to CPU on an otherwise
bit-identical activation and routing row. Independent same-input oracles
confirm the owner-specific outputs. The later layer-11 observation was
downstream of this change, so it is not a cache-only performance comparison.
Phase 5 remains open.

The current candidate also passed a 2026-10-22 bounded Phase 8 smoke: 7,498-token
8K-context retrieval plus same-service recovery, 130 CUDA CTests passed with two
optional fixture skips, and Python integration passed 163/163. This is
functional regression evidence, not a new timing confirmation. [Report](../../bench/results/2026-10-22-phase8-current-source-q2-profile-smoke/README.md).

A separate current-source MTP2 cancellation test matched all five committed
prefixes against two fresh references and recovered on the same service after
the client closed its stream. It strengthens one cancellation boundary set;
adaptive accepted-state drift and the two-live batch mismatch remain open.
[Report](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md).

Direct raw GDN captures from a 256-token adaptive chain confirm state drift
before the first recovery-token mismatch: at position 515, 786,405 recurrent
values and 30,719 convolution values differ, while delayed control stays
bit-exact through positions 515, 530 and 640. Each raw record matches the
accepted-prefix service hash. Phase 5 remains open. [Report](../../bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md).

A separate two-live trace now connects one owner switch to persistent state:
at position 71, layer-1 expert 11 moves VRAM→CPU on an exact-matched activation,
and the first changed committed GDN state is model layer 2. Its weighted part
delta explains the combined MoE output to `3.23e-9` maximum residual; exact
CUDA/CPU owner oracles pass. Both requests still match their six output tokens.
At position 68, all 36 GDN states were bit-identical. This is a single short
correctness trace; Phase 5 remains open. [Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A 3,000-slot repeat still moves layer-1 expert 11 VRAM→CPU and changes the first
committed GDN state at layer 2. Its activation differs from the 1,500-slot cell,
so the aggregate state delta cannot be used as a cache-size comparison. The
larger cap did not prevent the selected owner switch; Phase 5 remains open.

Correctness work has found a separate adaptive-recovery issue. In a 256-token
short–short–short Coder IQ1_M chain, adaptive recovery differed on 237/256
tokens, while delayed control was bit-exact at captured positions. At position
515, layer-21 expert 132 changes CPU→GPU ownership on the same input and route;
its owner-specific service rows match an independent oracle, but the CPU/GPU
rows differ in all 2,560 values (relative L2 0.016716). This explains one
contribution, not all later persistent-state drift. Current-source Coder MTP4
decode cancellation matched all 11 state fingerprints at four accepted-prefix
boundaries; early-prefill cancellation also matched all 11 recovery state
fingerprints. These qualify the tested points, not every cancellation boundary
or adaptive recovery. Opt-in cap-1 and default cap-64 batch graph
eviction/recapture now pass lifecycle stress coverage.
See the [owner transition](../../bench/results/2026-10-22-phase5-coder-longchain-owner-capture/README.md),
[raw state](../../bench/results/2026-10-22-phase5-coder-long-chain-raw-state-pair-pos767/README.md),
and [API cancellation](../../bench/results/2026-10-22-phase5-coder-api-cancellation-current-source/README.md)
records.

An MTP2 cancellation run also passed at five accepted-prefix lengths. Both
fresh exact-length controls matched every committed token and state
fingerprint; the canceled service returned `Hello Orin!` on recovery. Minimum
host/admission availability was 13.18/12.53 GiB with zero cgroup events.
This is a bounded cancellation cell only; adaptive long-chain drift and
two-live batch divergence remain open. [Details](../../bench/results/2026-10-22-phase5-coder-mtp2-cancel-state/README.md).

A fresh, supervised per-layer QSA trace now matches the serial MTP2 control at
accepted lengths 70, 72 and 74, then differs in all 12 QSA layers at lengths 76
and 77, starting at model layer 3. Both prompts still match serial for their
ten generated tokens. Minimum available host/admission memory was 16.55/15.10
GiB with no cgroup events. The split trace shows both indexer arrays and K/V
cache state change across all 12 layers from model layer 3 by length 76.
Per-token K/V/indexer and decoder-compute ablations retain the same divergence,
so neither batched path alone explains it. The cause and relation to later
output drift remain unknown. A concurrent duplicate-prompt control found both
batch slots' QSA hashes mutually matched but differed from serial,
while their ten-token outputs remained exact.
See the [batch-MTP report](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

Earlier QSA runs submitted the long request and one-token peer concurrently;
a harness name-check error meant they did not delay the peer after the first
output as intended. They still show QSA drift after the peer finishes. A
corrected MTP2 control submitted the peer after 48 solo-path tokens: QSA
hashes matched at common lengths 121/122, then all 12 indexer/KV hashes
changed from 124 through 163. Direct GDN captures were bit-exact at committed
positions 120/121 and differed across all 36 layers at 123 (relative L2 0.0142).
Output remained exact. The first state change is after handoff during batch-slot
work; the responsible operation and quality bound remain unknown.

Direct numeric captures at committed position 126 found GDN state drift in
all 36 layers for both MTP2 (relative L2 0.00973) and target-only (0.00841),
despite exact 96-token output parity. MTP2 is not required; numerical cause
and quality bound remain unknown.

A delayed target-only control matched GDN state through positions 116–118,
then first differed at 119/model layer 12 (relative L2 0.00780), with exact
output. MTP2 stayed exact at positions 120/121 and first differed at 123/model
layer 1. Per-token KV/indexer and decoder ablations retained MTP2's first QSA
mismatch at length 124, ruling out either batched path alone. State drift
persists; its source and quality bound remain unresolved.

A corrected opt-in layer-12 capture paired rows by explicit position/token and
recorded batch slot IDs. The delayed target-only run matched the serial 96-token
output exactly and matched all captured fields at position 118; at position 119,
layer-12 input `x` and every captured downstream field differed. The batch
scheduler averaged one row per window, so this run did not explain the separate
multirow mismatch. See the [capture report](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md).

A separate two-live target-only run averaged 1.96 rows across 96 windows and
reproduced slot 1's first output mismatch at token 60. At position 127 it
consumed the same token as its fresh serial control, while all captured layer-12
fields differed; input `x` relative L2 was 0.06058. The internal delta therefore
precedes the visible token change, but the model-wide origin remains unknown.
The selected positions and captured arrays repeated bit-for-bit in a second
supervised run; this is bounded to the same prompt pair and build.

At the earlier selected boundary, direct layer-12 committed-state capture found
slot 0 exact through position 70 and changed at 71 (relative L2 0.00379), while
slot 1 was already changed at position 68 (0.00822). Layer-12 input `x` changed
at the same selected positions. Slot 1's earlier onset remains unbounded; see
the linked capture report for paired state and activation metrics.

A six-token all-layer state capture then found the row mapping was reversed in
that run: physical slot 0 matched serial prompt 1, slot 1 matched prompt 0, with
36/36 GDN layers agreeing on each mapping. Slot 0 was exact at position 68 and
first changed at GDN layer 2 by position 71; slot 1 was already changed at
position 68, first at layer 5. Both six-token outputs matched their controls.
Slot-to-prompt assignment varied across runs, so these boundaries are kept
run-local and do not explain token 60.

A same-workload layer-1 MoE capture found exact inputs, GDN fields and shared
expert output for prompt 1 at position 71, while the combined MoE vector differs
in all 2,560 values (relative L2 `0.00086265`). The six generated tokens still
match serial. This narrows the selected boundary to routed expert output,
combination or related per-row state without identifying a specific expert or
operation. Minimum available RAM was 17.465 GiB, with zero cgroup memory events.
[Compact result](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-moe-output-summary.json).

A 96-token paired trace repeats the position-71 combined-output delta for
prompt 1 and reaches the known token-60 mismatch. By positions 118–127, both
requests already have changed layer-1 state, GDN fields, MoE inputs and shared
outputs. Minimum available RAM was 17.434 GiB; the added state capture makes
timing diagnostic only. [Selected-position results](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-moe-long-chain-summary.json).

An opt-in route/parts trace then showed prompt 1 keeps identical top-10 expert
IDs and weights at position 71, with nine expert outputs exact and only expert
11 changed. Weighting that expert's part delta reproduces the combined MoE
delta to a `3.24e-9` maximum residual. This pins the selected numerical delta
to expert 11's output path, without explaining its numerical cause. The six
output tokens still matched serial; minimum available RAM was 17.643 GiB.
[Compact result](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/two-live-layer1-expert11-summary.json).

## Near-term direction

The latest expert-11-first two-live capture mapped prompt rows through raw
routes and slot-tagged GDN state at positions 68/71. One row diverged by layer
5 at position 68; the other was exact then but diverged by layer 6 at position
71 after an exact layer-4 MoE output. The unmatched row also had changed layer-4
activation and router weights, so its expert output remains unattributed.
[Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/layer4-profile-e11-first-positions68-71/README.md).

A follow-up isolates the position-68 expert-248 owner transition. On the same
activation, the independent CPU/GPU oracle differs at relative L2 `0.0113` by
default and is bitwise equal with `STRATA_NATIVE_CPU_Q8_1_DOT=all`. The default
two-live service row changes only expert 248's part (combined output relative
L2 `0.0028174`); in the separate Q8_1-all service cell the same expert's
CPU→CUDA transition has exact parts and combined output. State stays exact for
one request through position 71; the other has only a tiny first difference
at layer 30 (relative L2 `5.84e-9`). Different route histories between selector
cells prevent a whole-model causal claim. Phase 5 remains open.
[Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/layer4-expert248-q8-all-owner-pair/README.md).

1. Continue resolving batch-MTP output divergence: capture earlier layer
   boundaries and logits around the reproducible multirow drift, then isolate
   the first recurrence or verifier operation that changes the row. Extend
   accepted-prefix direct-state and long-chain
   recovery coverage, widen cancellation boundaries beyond the passing Coder
   MTP4 decode/prefill points, and keep adaptive migration opt-in until its
   long-chain state contract is bounded.
2. Continue Phase 6 only on qualified candidates: finish supported interactions,
   held-out confirmation and response-model diagnostics, then report energy and
   Pareto tradeoffs with physical-memory, clock and uncertainty context.
3. Update detailed status and integration notes as evidence lands. Commit and
   push when each phase gate is actually complete; preserve the six-GiB host
   headroom and separate workspace reserve throughout.

Models stay under `~/models/`; build products, credentials and local agent
configuration stay out of Git. Do not combine host RAM and CUDA capacity into a
single memory figure.

A dispatch-owner follow-up maps the selected layer-1 position-71 Coder row exactly: expert 11 moves from primary VRAM in serial to CPU in batch, and its recorded CPU output matches the batch part within `5.0e-11` (serialization rounding). This associates the isolated expert delta with an owner change but leaves the numerical cause and later token-60 relationship unresolved. [Details](../../bench/results/2026-10-22-phase5-coder-batch-gdn-layer-capture/README.md).


The same-input native expert oracle confirms the prompt-1 owner transition (serial GPU and batch CPU outputs each match their owner-specific oracle exactly). Prompt 0's serial CPU output and batch CPU dispatch 3505 both match the exact single-token CPU oracle, to JSON serialization precision (`5.0e-11`). The earlier reported 2.19 relative-L2 difference compared against prompt 1's oracle activation by mistake. Prompt 1's CPU/GPU difference remains real for that activation and needs broader numerical qualification.

A temporary expert-11-first residency profile made the paired layer-1 MoE
output exact and moved the first changed committed GDN state to layer 4. Layer 2
still switches expert 164 from VRAM to CPU with a same-input, oracle-confirmed
owner arithmetic difference. This narrows the correctness investigation only;
it is not performance evidence or a supported profile. The trace joiner now
rejects owner/verifier route mismatches. [Details](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).

A new opt-in IQ3_S/Q2_0 CPU Q8_1 path matches CUDA bit-for-bit for two captured
layer-21 activations, but adaptive recovery still differs on 254/256 tokens in
the paired long-chain test. Router weights and committed state already differ
before the targeted expert output can explain the drift. Phase 5 remains open;
[details](../../bench/results/2026-10-22-phase5-coder-iq3s-q2_0-layer21-parity-intervention/README.md).

A separate two-live six-token check with opt-in Q8_1 parity matched both serial
outputs, including an exact CPU↔GPU expert-248 owner transition. One later GDN
state differed only at relative L2 `5.84e-9`; the other stayed exact. This
narrows one case and does not close Phase 5. [Details](../../bench/results/2026-10-22-phase5-coder-e11-first-q8all-two-live/README.md).

The new shared CPU selector also rebuilt for HIP and SYCL on maestro1, with both
service help checks and the HIP selector-contract check passing. This is x86
compile/startup evidence only. [Build record](../../bench/results/2026-10-23-phase5-maestro1-iq3s-q2-selector/README.md).

The seven-block Coder cache × context confirmation also has a new retrospective
rail-energy analysis: `VIN_SYS_5V0` per output token was 7.42% lower at 8K and
7.05% lower at 16K with the larger requested cache. These are background-
contaminated named-rail estimates, not process or whole-device energy, and do
not change the profile direction. [Details](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-long-interaction-confirm7/rail-followup/README.md).

The separate short Coder task's seven-block cache confirmation shows an
11.19% lower `VIN_SYS_5V0` estimate per output token with the larger cache at
8K. These request-window rails include idle/background power and are not
whole-device energy. [Details](../../bench/results/2026-10-21-phase6-coder-current-source-cache-context-confirm7/rail-followup/README.md).

A held-out 256-token adaptive short-chain recovery test differed from the
initial output at 237 positions and had changed accepted-state hashes at every
prefix; the delayed control stayed exact. This extends the known mismatch but
does not bound it or locate its cause. [Details](../../bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-direct-division-state-bound-128pos/open-response-short-chain-256pos/README.md).

A two-live target-only check with Q8_1 forced to `all` matched slot 0 for 96
tokens but slot 1 first differed at index 66. Minimum physical/admission
availability was 17.54 GiB. This single correctness cell does not identify the
cause or qualify performance; [details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

The follow-up captured that row's logits at position 133: both arms used input
token 3008, but the top two reversed (2100 versus 5435). This locates the
changed output at verifier logits while leaving its upstream cause open.
An all-layer state capture found a tiny first recurrent-state delta at model
layer 10 (relative L2 `1.09e-7`), which grows by layer 12; the arithmetic cause
at that later position was unresolved. [Full capture report](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).
Repeated layer-10 traces show the first changed intermediate is the recurrence
output `y` at relative L2 `7.70e-8`; projected output returns to exact values.
State is exact through position 82; at position 83, layer-9 MoE expert 233
switches VRAM→CPU and its owner-specific output accounts for the first
captured state delta. Same-selector CPU/GPU oracle outputs match their
respective service parts exactly. Phase 5 remains open.


A 3,000-slot expert-cache request kept layer-9 expert 233 on VRAM for both
serial and batch at the exact position-83 input. Its ten routed parts and MoE
output matched bit-for-bit; the 1,500-slot cell had a CPU owner transition and
small delta. This is a narrow correctness intervention, not a full-sequence or
performance result. Phase 5 remains open.


The 3,000-slot request did not restore full two-live sequence parity: slot 0 matched
96 tokens, while slot 1 diverged at token 60 (versus 66 in the 1,500-slot cell).
The targeted expert-233 output was exact with GPU residency, but that local fix
did not carry through the full sequence. Phase 5 remains open.


A repeated exact-input position-83 capture again found bit-identical expert
parts and combined MoE output at a 3,000-slot request; expert 233 remained resident on
VRAM in both paths. The 96-token two-live mismatch persists.


The 3,000-slot sequence investigation is still unsettled. One run found a layer-25
state delta at position 83, but repeated and combined captures at that position
were exact. Separate same-prefix captures at position 127 point to layer-24
state history and intermediate `h` when output first differs, but do not prove
causality. Phase 5 remains open.


The same-run position-112 capture is the strongest localization so far: layer 24
first differs in committed GDN state; its inputs and QKV are exact, and `h` is
the first changed stage. The state delta appears after sampled exact states at
positions 83 and 96, ahead of slot 1's first changed output at index 60. The
targeted CUDA parity tests pass but do not cover integrated scheduling. Phase 5
remains open.


A same-run onset sweep found layer-24 state/intermediates exact through position
104, with the first sampled difference at position 108: `h` changes while
`x`/QKV/gate/beta/z are exact; recurrent and convolution state then diverge.
Slot 1's output first changes at index 60 (position 127). The cause remains
unresolved.

A supervised repeat of the 104–108 layer-24 sweep changed state earlier than
the prior run: first at 105 with `x` changed, then `h` first at 107–108. The
prior run first changed at 108 with `h`. Output still diverged at index 60.
Verifier row IDs moved between runs; pairing was confirmed using captured input
tokens. The cause and stable onset remain unresolved, so this remains
correctness localization rather than a performance result.

The attempted layer-23 tensor comparison could not capture a two-live batch row:
the diagnostic supports one-row windows, while both requests were grouped. A
one-live request used the serial verifier path (header slot `-1`) and is not a
batch comparison. The QSA-to-layer-24 input boundary remains unlocalized; this
capture limitation is recorded as unsupported rather than a pass.

A repeated positions-80–84 state sweep found a larger slot-0 mismatch: it
returned all 72 serial output IDs, but its layer-10 state differed from position
80 (relative L2 `5.83e-3`). A same-run all-layer capture found the first changed
GDN state at layer 5 (recurrent relative L2 `5.41e-5`); slot 1 was exact at
position 80. The repeated sweep reproduced the same metrics, so multi-live
persistent-state parity remains unresolved even when output tokens match.
An additional layer-5 sweep sampled positions 78–80 and found slot-0 recurrent
state already differed at position 78 (`9.55e-5` relative L2); at position 80,
the convolution section matched again while recurrent state remained changed.
[Details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

A same-run capture localized an early slot-0 perturbation: layer-4 expert 218
moved VRAM→CPU with exact inputs/routes, and the independent oracle matched each
service output to its corresponding GPU/CPU result. The following layer-5 stage
first changed at `x` for the same token/position; layer-5 state was exact at the
prior sampled position. This strongly supports owner-dependent arithmetic as
the source entering layer 5, though downstream propagation remains unproven.
[Details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

Raising the requested expert-cache slot count to 3,000 left the same layer-4 expert 218
VRAM→CPU owner change and reproduced the same layer-5 `x`/state delta for the
same activation. This cache increase does not resolve the measured cell.
[Details](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

Moving expert 218 to rank 0 in a temporary profile kept it on VRAM for serial and batch at the exact same position-77 activation; its parts, combined MoE output, and layer-5 stage/state were then bit-identical. This repairs that local state perturbation, but not the separate slot-1 sequence mismatch (first difference at 66). At positions 76/77 slot 0 first differs later at model layer 32; layer-30 MoE output is exact while layer-31 MoE input already differs. Phase 5 remains open. [Intervention analysis](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/expert218-intervention-analysis.json).

A per-layer GDN hash trace under the expert-218-first profile found prompt 0 first differing at prefix 70 (ordinal 30) and prompt 1 at prefix 82 (ordinal 8), while output slot 1 still first differed at token 66. A direct position-82 state capture instead found prompt 0 first differing at model layer 32; later prompt-1 traces show tiny layer-10 `y`/state deltas with exact layer-9 MoE data. Internal batch row assignment varies between runs, and state onset varies, so the cause is still open. [Analysis](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/expert218-intervention-analysis.json).

A paired 72-token screen at one and eight expert workers produced the same
pattern: slot 0 matched and slot 1 first diverged at output index 60. Worker
count did not shift the mismatch in this cell, but its underlying cause remains
unresolved. Minimum admission availability was 14.17/14.16 GiB with zero
cgroup events. [Report](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

A narrow layer-22 expert-rank swap made the sampled layer-22 MoE and following
boundary exact, and slot 1's full 96-token output matched. Its recurrent state
still differed by layer 9 at terminal position 162. At position 105, layer-39
MoE and its boundary were exact; the first changed sampled stage was layer-40
GDN `h` (relative L2 `8.700e-5`). This narrows one sampled path but does not
distinguish pre-existing recurrent state from row-context recurrence arithmetic.
The opt-in multirow boundary capture passes the focused Orin parity tests;
maestro1 backend rebuild is pending while its root filesystem remains 99% full.
Phase 5 remains open. [Trace notes](../../bench/results/2026-10-23-phase5-coder-two-live-target-q8all/README.md).

A same-profile position-104 follow-up found the layer-39 pre-branch residual
and routes exact, but the branch output changed (relative L2 `3.6151e-5`); only
expert 50's part changed as it moved GPU→CPU. On that captured activation, an
independent oracle matched the serial service part to GPU and the batch part to
CPU exactly. Layer-40 input `x` and committed recurrent state were already
different at position 104. This supports an earlier owner-dependent
contribution in this sampled run; the first source is position-dependent and
the general two-live state drift remains unresolved.

A new current-source Coder IQ1_M prefill-chunk × expert-cache screen completed
three randomized blocks: chunk 128 reduced client total time 67.4%/69.6% at
requested caches 1,500/3,000 slots for a 7,501-token task. The median
cache-by-chunk time interaction was −9.8%, with minimum physical/admission
availability 14.19/14.14 GiB and zero cgroup events. This is descriptive
screening evidence without confidence intervals; the distinct seven-block
held-out confirmation is reported separately below. [Screen report](../../bench/results/2026-10-23-phase6-coder-prefill-cache-screen3/README.md).

A seven-block held-out Coder IQ1_M confirmation is complete: all 28 measured
cells returned the exact 46-token answer for the distinct 7,501-token archive,
with zero cgroup memory events and at least 14.19 GiB physical/admission
availability. Chunk 128 lowered client total time 67.71% (95% paired-block
interval 67.55%–67.95%) at 1,500 requested cache slots and 68.72%
(68.56%–68.85%) at 3,000; the cache-by-chunk interaction was −3.13%
(−5.43% to −1.93%). Decode-throughput intervals included zero. This is scoped
to Coder IQ1_M, FP16 KV, MTP off, 8K and this archive task; no default is
promoted, and broader Phase 6 interactions and energy/Pareto scope remain open.
[Full report](../../bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/README.md).
Retrospective `VIN_SYS_5V0` energy per output token was 66.27%/67.15% lower
with chunk 128 at the two cache settings, but the named rail includes idle and
background activity and is not process-attributed or whole-device energy.
[Rail analysis](../../bench/results/2026-10-23-phase6-coder-prefill-cache-confirm7/rail-followup/README.md).


A new three-block current-source MTP window screen (off/2/3/4) on one short
Coder IQ1_M retrieval prompt passed all 12 cells with paired output parity.
MTP3 showed +5.24% median decode throughput; MTP4 was effectively flat. MTP2
had a large -57.96% outlier, so no MTP2 timing conclusion is supported. This
is screening only, not a default or broad quality/state claim.
[Report](../../bench/results/2026-10-23-phase6-coder-mtp-window-screen3-current/README.md).

A seven-block MTP-off/MTP3 replication on the same 512-token prompt gave +4.34%
median decode throughput (paired bootstrap 95% interval +3.86% to +5.57%) with
response-content parity in all pairs. This is same-prompt replication, not
held-out confirmation, and the no-trace campaign does not test persistent
state. [Report](../../bench/results/2026-10-23-phase6-coder-mtp3-window-paired7-same-prompt/README.md).

A near-limit MTP3 screen showed a workload-length interaction: across three
paired blocks, MTP3 decode throughput was 6.01% lower than MTP-off on the
7,501-token request (95% interval 6.08%–5.56% lower), while it was 4.34% higher
on the 512-token prompt. Total request time on the near-limit prompt rose only
0.67% because prefill dominated. This is screening evidence for these workloads,
not a default decision. [Report](../../bench/results/2026-10-23-phase6-coder-mtp3-window-long-screen3/README.md).

A seven-block held-out retrieval confirmation returned the exact expected
answer in all 14 MTP-off/MTP3 cells. MTP3 decode throughput improved 10.25%
median (95% interval +8.98% to +10.49%), though two MTP3 cells had severe
prefill/TTFT outliers; stable end-to-end latency is not established. [Report](../../bench/results/2026-10-23-phase6-coder-mtp3-heldout-retrieval-confirm7/README.md).

An MTP3 accepted-prefix probe matched MTP-off token IDs and all persistent-state
fingerprints at 31 shared commit boundaries over a 64-token chain (33/60 drafts
accepted). This is a bounded transaction check; adaptive long-chain and
multi-live correctness remain open. [Report](../../bench/results/2026-10-23-phase5-coder-mtp3-accepted-prefix-64/README.md).


Current-source MTP3 state parity also passed for 64 generated tokens: identical
token IDs and all nine state fields at 31 shared commit boundaries and final
state. It covers the deterministic harness prompt only.
[Report](../../bench/results/2026-10-23-phase5-coder-mtp3-accepted-prefix-64/README.md).

A three-block factorial MTP3 × FP16/INT8 KV screen passed all 12 short-task
cells. MTP3 decode gains were 7.78% and 7.89%; the MTP-by-KV interaction
interval included zero. The screen covers one held-out 512-token workload only.
[Report](../../bench/results/2026-10-23-phase6-coder-mtp3-kv-short-screen3/README.md).

The factorial runner was generalized from MTP4-only to windows 2, 3 and 4 with
a selected-window summary label. Its focused suite passes 12/12; the full
Python integration suite now passes 173/173.

The full three-block MTP3 × KV × prompt-length screen passed all 24 cells. It
found ~8.4% higher decode on the 512-token task but 3.5–4.7% lower decode on
the 7,501-token task; total long-request time rose under 0.7%. The broad MTP ×
workload effect is clear in this screen, while the three-way interaction interval
includes zero. [Report](../../bench/results/2026-10-23-phase6-coder-mtp3-kv-length-screen3/README.md).

Named tegrastats rail energy was integrated for all 24 request windows. On the
short task, MTP3 reduced GPU/SOC rail joules per output token by about 7% while
raising CPU rail use about 4–5%; the system rail was down about 3%, with the
FP16 interval crossing zero. On the near-limit task, system-rail energy/token
rose about 0.5% for both KV formats. These are three-block rail estimates that
include idle/background load; they are not process-attributed or summed device
energy. Phase 6 energy/Pareto work remains open. [Report](../../bench/results/2026-10-23-phase6-coder-mtp3-kv-length-screen3/README.md).

### Latest Phase 5 check: layer-9 expert-233 exp2f candidate

Seven captured activations had exact CPU/CUDA gate/up outputs. Default CPU
SwiGLU matched CUDA's packed hidden Q8_1 and final output on six; an opt-in host
exp2f candidate matched on all seven. In a two-live 72-token service replay,
expert 233 was confirmed CPU-owned at layer 9 / position 83. The direct
committed GDN state matched serial for slot 1 (same-profile control first
differed at layer 10); slot 0 still first differed at layer 5. With identical
CPU ownership, route, weights and activation, the no-selector batch output
first differed at token 66 for slot 1, while the exp2f candidate matched all
72 serial tokens. Its first accepted-prefix mismatch moved from batch position
84 to 89; slot 0 remained at 75. This repairs one output mismatch and delays
but does not eliminate state drift, so Phase 5 remains open. A reversed-order
repeat reproduced the result; a same-profile 128-token run kept slot 1's output
exact while the first state mismatch still arrived at position 89. This is the
same prompt pair, not held-out confirmation. The selected CPU oracle matched
CUDA's hidden Q8_1 and down outputs, and the captured service
expert part matched that oracle bit-for-bit. Details and
limits are in the [experiment report](../../bench/results/2026-10-24-phase5-coder-layer9-expert233-residency-intervention/README.md).

### Latest Phase 6 check: MTP4 × KV × workload screen

A randomized three-block MTP-off/MTP4 screen passed all 24 cells for FP16 and
INT8 KV on 512-token and 7,501-token Coder IQ1_M retrieval prompts. MTP4 raised
decode throughput by 10–11% on the short prompt but lowered it by 9–11% on the
near-limit prompt; client-total intervals included zero in all four cells.
The workload-length tradeoff argues against a global MTP4 choice. Minimum
physical/effective admission availability was 16.83/15.69 GiB; no energy
analysis was performed. This is screening evidence on fixed prompts, not
held-out confirmation. [Report](../../bench/results/2026-10-24-phase6-coder-mtp4-kv-heldout-length-screen3/README.md).

### Latest Phase 5 check: MTP4 accepted-prefix state

With the correct draft-model config loaded, a 64-token MTP4 run matched MTP-off
token IDs and all nine persistent-state fields at final state and 29 shared
commit boundaries (35 of 84 drafts accepted). This extends the deterministic
transaction check from MTP3 to MTP4 for one 512-token prompt; multi-live and
long-chain state gates remain open. An initial config-selection error that
loaded no draft model was excluded. [Report](../../bench/results/2026-10-24-phase5-coder-mtp4-accepted-prefix-64/README.md).

### Latest Phase 6 check: held-out MTP4 short-task confirmation

Seven randomized paired blocks on a distinct 512-token Coder retrieval prompt
passed all 28 answer checks. MTP4 improved decode throughput 13.22% with FP16
KV and 13.72% with INT8 KV; the KV interaction interval included zero. Total
time improved slightly with INT8 KV and was unresolved with FP16. The separate
near-limit screen found an MTP4 decode slowdown, so no default is promoted.
One low-throughput FP16 control outlier is retained; the exploratory response
model had large residuals, so paired bootstrap estimates remain primary. Energy
was not analyzed. [Report](../../bench/results/2026-10-24-phase6-coder-mtp4-heldout-short-confirm7/README.md).

The MTP4 accepted-prefix state check now also passes 256 generated tokens and
348 tokens to natural EOS from the same deterministic prompt. Token IDs and all
nine state fields matched at final state and 115 / 157 shared commit boundaries.
This covers uninterrupted generation only; multi-live state drift remains
unresolved. [Report](../../bench/results/2026-10-24-phase5-coder-mtp4-accepted-prefix-long-chain/README.md).

The same-profile 128-token two-live exp2f replay still matched both serial
outputs (120 and 128 tokens), while accepted-prefix state first differed at
batch positions 75 and 89. Direct snapshots found slot 0 first changed at GDN
layer 32 / position 75 (relative L2 0.003175); slot 1 was exact at position 75
and first changed at layer 12 / position 89 (relative L2 `9.16e-5`). Minimum
physical availability was 17.73 GiB, with zero cgroup pressure/OOM events.
Output parity therefore still does not establish multi-live state parity; no
profile is qualified. At slot 1 / position 89, routes, activation, layer-9
expert parts/MoE output and layer-10 stage fields matched serial even though
expert 233 moved GPU→CPU; state first differed at layer 12. [Report](../../bench/results/2026-10-24-phase5-coder-exp2f-boundary-state-pair/README.md).

An opt-in QSA hash trace found slot 0 first differed at position 74 in layers
31/35/39/43/47 and slot 1 at position 88 in layers 15/19/23/27/31/35/39/43/47,
across both indexer and KV state. Both 32-token outputs remained exact; slot 1
GDN state first differed at layer 12 / position 89. This locates additional
state boundaries but not their cause. [Report](../../bench/results/2026-10-24-phase5-coder-exp2f-layer11-position89/README.md).

### Latest Phase 5 check: same-run owner/state boundary

A same-profile capture found prompt 1's all-layer GDN state exact at positions
86 and 87, then first changed at layer 12 / position 88. Layer-10 stages were
exact at 87 and 88. Layer-11 routes, activation and all expert outputs were
exact at 87; at 88, expert 114 moved GPU→CPU and was the only changed part.
An independent same-activation oracle matched serial service to GPU and batch
service to CPU bitwise. Both requests still emitted 32 exact tokens. This
localizes a sampled source of state movement but does not bound longer state
drift or quality impact. No exp2f fix was supported for this expert. [Report](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md).

### Latest Phase 6 check: worker/transfer Pareto view

The seven-block held-out worker × transfer study now includes a descriptive
four-cell Pareto table for TTFT, request/decode time and three named energy
rails. All four settings are nondominated because latency, CPU/CV and GPU/SOC
rail tradeoffs cross; these rails include background activity and are not
whole-device energy. Per-cell headroom and physical disk traffic were not
retained, so this does not select a serving profile. [Table](../../bench/results/2026-10-24-phase6-coder-worker-transfer-confirm7/README.md#workload-specific-pareto-view).

A temporary Coder IQ1_M profile moved layer-11 expert 114 to rank 0. Its
targeted prompt's layer-10/11 outputs and all committed GDN state matched at
position 88, and the 72-token accepted-prefix mismatch moved from batch
position 89 to 99. The two-live output still diverged at token 60 for one
logical slot. This local residency intervention does not qualify a profile or
close Phase 5. maestro1 still has only 1.1 GiB free, blocking current-source
HIP/SYCL rebuilds. [Report](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#expert-114-rank-0-residency-intervention).

A second supervised 72-token run with expert 114 at rank 0 reproduced the
accepted-prefix GDN hash onset: the prompt paired to serial control 1 first
changed at batch position 99 / serial prefix 97 (18/36 allocations), while the
other prompt first changed at position 75. Both runs' output records had slot 0
exact and slot 1 first differing at token 60. This replicates the sampled
pattern but still provides no state-drift or quality bound. The replication
retained 17.74 GiB minimum physical availability with no cgroup pressure/OOM
events. [Report](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#expert-114-rank-0-residency-intervention).

Direct numeric GDN snapshots at positions 98/99 under the same profile show
state drift before the token-60 output mismatch: the prompt mapped to serial
control 0 first differs at layer 5 (relative L2 `4.18e-7` at position 98),
and control 1 at layer 24 (`8.67e-5`). These same-position captures do not
identify the upstream operation or bound quality impact. Minimum physical
availability was 17.65 GiB with no cgroup pressure/OOM events. [Details](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#numeric-state-at-the-later-divergence).

A new same-profile trace found another local owner delta before persistent
state drift: layer-22 stages matched exactly; at layer 23, routes and activation
matched, while expert 191 moved GPU→CPU and was the only changed expert part
(relative L2 `1.74e-4`). The combined MoE output changed by `2.11e-5`; the
accepted-prefix GDN hash first changed at batch position 99. The independent
native oracle matched service GPU/CPU parts bitwise to their respective
oracles. This is a second sampled owner-specific perturbation, not a complete
cause or quality bound. [Analysis](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#layer-23-owner-transition-in-the-rank-0-intervention).

For the earlier prompt, the same-profile position-75 trace found layer-30 stage
fields exact, then layer-31 MoE activation and routes already differed before
expert execution (activation relative L2 `5.27e-4`; owners unchanged). The
combined layer-31 output differed by `0.006014`, followed by first numeric GDN
difference at layer 32. Layer-4 expert 218 also changed owner at this position
but its exact-input output stayed bit-identical. The responsible layer-30/31
boundary operation remains unknown; a requested layer-3 stage dump was not
available. [Report](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#earlier-prompt-layer-3031-boundary).

The follow-up directly confirms that layer-30 stage fields match, but
layer-31 MoE input and routes differ before expert execution; all expert owners
are unchanged. The same run first changes GDN at layer 32. The change therefore
lies in the intervening residual/normalization path or an earlier hidden-state
source, not the layer-31 owner choice; its exact operation remains unknown.

The `STRATA_NO_MULTI_GR=1` single-factor ablation left the position-75
layer-31 activation/routes, layer-32 first changed GDN layer, and token-60
output mismatch unchanged. This kernel-specialization flag does not repair the
sampled state boundary; no speed inference is made. [Run and paired analysis](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#strata_no_multi_gr-diagnostic-ablation).

The opt-in `STRATA_GR_V3=1` fused hyperconnection read is promising in this
sample. At position 75 it restored exact layer-30/31 fields and GDN state; both
72-token outputs matched. A 128-token extension again matched both serial
outputs (120-token stop and 128 tokens), but accepted-prefix state hashes still
first changed at positions 100 and 105. This delays the earlier mismatch and
fixes the output divergence in this prompt pair, but does not close the
long-chain state gate or qualify a profile. [Report](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#strata_gr_v3-1-boundary-intervention-and-128-token-extension).

The current Orin CTest run completed 132/135 registered cases, with two
fixture-dependent IQ tests skipped and `pool_test` unable to find its default
`pack/full/experts.bin`. Supplying the existing one-layer Q2_0 fixture through
`STRATA_TEST_EXPERTS_BIN` made the pool test pass its serial parity, completion
and repeated-batch checks. Minimum physical availability was 19.19 GiB. The
new model-width verifier convolution parity test passed all T=1..8 windows and
split offsets; no kernel change was needed. Phase 5 multi-live persistent-state
drift is still open, as are broader Phase 6 interaction/energy gates. [CTest
report](../../bench/results/2026-10-24-orin-cuda-functional-ctest/README.md).

A token-aligned GR-V3 state capture now shows all 36 committed GDN layers exact
at model position 103, then layer 20 first changed at position 105 while both
outputs remained exact. Layer-20 `x` and `qkv` matched at p105; `h` was the
first changed stage field. The earlier batch-hash/serial-prefix offset compared
pre-window batch state with post-commit serial state, so those labels are not
the same numeric boundary. [Analysis](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#committed-state-alignment-at-positions-103105).

An exact-activation oracle confirmed that expert 137's GPU→CPU owner change
contributed to the layer-19 output delta at p104. Moving this expert to rank 0
restored exact layer-19 outputs and layer-20 committed state through p105, but
slot 1 still diverged at token 66; the previous profile matched all 72 tokens.
The intervention isolates a local contributor without fixing end-to-end
behavior. [Details](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#expert-137-residency-intervention).

A reversed-slot repeat confirms the expert-137 intervention's local repair is
slot-independent; the later token-66 mismatch follows original prompt 1, while
original prompt 0 stays exact. All GDN state remains exact through matched
position 105 in this 72-token pair. The cause of later prompt-specific drift is
still open. [Details](../../bench/results/2026-10-24-phase5-coder-exp2f-layer10-11-boundary-87-88/README.md#expert-137-residency-intervention-with-reversed-logical-slots).

Phase 8 portability follow-up: the five shared C++ files changed since the
previous maestro1 snapshot rebuilt successfully for HIP and SYCL at one job.
HIP's host memory-budget CTest passed; both service help checks passed. The
current SYCL runtime had no available device, so this adds no accelerator
execution evidence. [Build record](../../bench/results/2026-10-24-phase8-maestro1-incremental-current-shared-build/README.md).

Phase 5 is closed for the tested Orin single-live static-routing transaction
and graph scope. MTP accepted-prefix, long-chain and bounded cancel/recovery
checks passed; multi-live batch decode and adaptive expert migration remain
excluded because their persistent-state gates fail. [Closeout](PHASE5_CLOSEOUT.md).

Phase 6 is closed for measured Orin factor domains: held-out cache/context, prefill/cache, worker/transfer, MTP/KV/workload, and graph/speculation cells have oracle checks and block-level uncertainty. No single Pareto profile is promoted; energy rails include board background. [Closeout](PHASE6_CLOSEOUT.md).

Current E6 diagnostic: identical 65K prompt boundaries and generated tokens
produce different persistent GDN bytes by accepted prefix 8 when adaptive
residency is enabled. The first raw difference is in zero-based model layer 2;
the distinct 8K replay-boundary dump first differs in GDN allocation 3. This
localizes state divergence but not its cause. E6/E7 remain open; see the
[paired diagnostic](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/adaptive-long-prefix-state-diagnostic.md).
A comparison of the layer-0/1/2 traces across the first seven generated
positions found one owner change: layer-1 expert 3 changes GPU→CPU at position
65,540 after adaptive swap `1:320>3`; layer-2 routes and owners match, with its
first input delta at the same position. A fresh paired capture followed this
through layer-2 GDN: `x` shifted slightly; `qkv` and `h` remained exact; gate
and beta changed; and the layer-2 recurrent state first differed after that
token. The independent FP64 recurrence and same-prestate gate/beta
counterfactual confirm the local update effect, but not a live forced-owner or
whole-model cause. [Counterfactual report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/layer1-expert3-layer2-gdn-counterfactual-65540.md).

The layer-13 state sequence now shows identical state through the update at
position 65,538; the first sampled divergence is the post-state after token
1,928 at position 65,539 (relative L2 `2.3215e-5`). Captured post/pre states
are exactly continuous within each arm, outputs match, and both runs retain the
six-GiB floor. This is onset timing, not root-cause attribution; next capture
the layer-13 GDN stages at 65,539. [Comparison](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/gdn-layer13-state-sequence-comparison.json).

At the first layer-13 state-divergence update (position 65,539), the incoming
recurrent state matches exactly. `x` differs by relative L2 `1.80e-7`; projected
`qkv` differs by `4.26e-5`, followed by recurrent `h` at `3.03e-5`. The update
creates a `2.32e-5` post-state difference, while output tokens remain identical.
The projection's sensitivity versus upstream arithmetic is still unresolved.
[Comparison](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/gdn-layer13-position65539-comparison.json).

The layer-12/13 boundary at position 65,539 already carries the small delta:
layer-12 residual relative L2 `1.11e-7`, MoE `2.13e-7`, next-layer activation
`1.53e-7`; layer-13 GDN `x` is `1.80e-7`. Both arms returned identical tokens
and stayed above the memory floor. Next localize across earlier layers.
[Boundary comparison](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/layer12-boundary-position65539-comparison.json).

The all-layer trace at position 65,539 first differs at layer 5: only expert
220's row changes with matching input/routes (relative L2 `1.14e-7`), followed
by a `5.77e-8` combined-output delta. The adaptive schedule promotes expert 220
there before dispatch; direct owner/oracle confirmation is next. The delta
appears in layer-6 input and routes remain equal until layer 17. [Trace](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/all-layer-position65539-comparison.json).

Direct owner capture and independent Q2_0/Q8_1 oracle confirm layer-5 expert
220 changes CPU→GPU at the first sampled output delta; identical-input service
rows match their native owner replays bit-for-bit. CPU/GPU row difference is
`1.14e-7` relative L2, and both agree with the independent FP64 oracle within
`9.74e-8` / `6.14e-8`. This locally verifies the first changed expert row;
later adaptive swaps may still contribute. [Report](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/layer5-expert220-owner-oracle-position65539.json).

Layer-7 expert 225 is a later contributor: its input shifts, but CPU and GPU
replays each produce the same expert row on both captured inputs; service rows
match their respective owners bit-for-bit, differing by `1.05e-7`. Route
weight and shared output also move, so the combined MoE delta has more than one
component. [Oracle](../../bench/results/2026-10-30-e6-q2-identical-65k-request-repeat/layer7-expert225-owner-oracle-position65539.json).

Live one-position owner interventions now cover layer-1 expert 3 at position
65,540 and layer-5 expert 220 at position 65,539. The latter forced CPU row
matches the fixed arm byte-for-byte with exact inputs/routes; its full-state GDN
comparison first grows beyond `1e-8` at layer 15, without a matched repeat to
attribute that drift. The former matched adaptive layer-1/2 captures exactly.
Requests passed above 8.4 GiB RAM. Repeated layer-5, layer-7 and layer-13 CPU
interventions and adaptive controls match byte-for-byte within arms. All three
owner changes produce reproducible later GDN drift (first material at layers
15, 16 and 18), with identical output tokens. These are bounded state effects,
not quality or speed benefits. HIP and SYCL built on maestro1; only HIP could
start without device limits. E6/E7 remain open. [Reports](../../bench/results/2026-10-31-e6-q2-owner-intervention/README.md).

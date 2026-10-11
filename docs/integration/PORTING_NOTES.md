# Integration notebook and future Strata + Splash work

## 2026-10-09 — Start at the measurement boundary

The first implementation adds Python harnesses outside the engine. No NInfer
runtime source has been promoted. The pinned Strata runtime and this branch have
identical `src/`, `include/`, top-level CMake and vendored ggml contracts at this
checkpoint. Build and request controls must precede an execution-path change.

The following boundaries should carry over to a Splash integration, subject to
reading and pinning that engine's actual source and license:

| Reusable method | Orin implementation | Apple/Splash question to resolve |
| --- | --- | --- |
| Pin inputs, preserve references | Strata `0be090c`, NInfer `b07248f2`, immutable import manifest | Pin Splash and preserve its notices before adapting any source |
| One physical memory authority | Linux MemAvailable and cgroup ancestor ceilings; CUDA is an additional constraint | Establish platform physical availability and Metal allocation constraints without adding their capacities |
| Exact model/format identities | Explicit Coder IQ1_M, Q2_0 MTP, tokenizer/template hashes | Map actual Splash codecs and tensor shapes; never assume compatible packed weights |
| Prepare inputs before execution | Hash formatted token IDs, retain actual lengths | Keep tokenizer/template comparisons separate from operator comparisons |
| Separate observations from qualification | Successful command exit does not establish numerical parity or speedup | Metal compilation, operator execution, request behavior and sustained service need distinct gates |
| Own process lifecycle in the harness | One cooperating campaign lock, child process groups, bounded TERM/KILL, partial JSON | Implement equivalent process cleanup and platform telemetry; Linux `/proc` is not portable |
| Promote narrow seams | Existing Strata scheduler, physical owner and persistent state remain authoritative | Identify the existing Metal/CPU owner; avoid a duplicate scheduler or memory ledger |
| Independent correctness before schedules | Codec/math oracle and accepted-prefix state gates remain pending | CPU FP64 or independent exact codec reference; directly inspect recurrent/KV state for speculation |

`tools/integration/run_control.py` supervises explicit commands. It samples
physical availability, cgroup-v2 ancestor limits, swap, process-group RSS,
faults/I/O and host disk counters, and preserves raw tegrastats output when
available. It does not sum CPU and GPU capacity. The six GiB floor cannot be
lowered through this runner. The engine's separate three GiB workspace reserve
is unchanged. The lock excludes other cooperating harness instances; it cannot
prevent an unrelated application from using the board. Check active model
processes before a campaign. Sampling is a pressure guard, not an allocation
reservation or proof of absence of sub-sample memory peaks.

`control_manifest.py` hashes explicitly supplied files and records compiler,
power-mode, clock and embedded-CUDA-image observations. Source revision is a
declared field: archived source trees must be created from that revision and
kept unchanged. Use the artifact list to include native shards, prepared dense
and expert packs, MTP files, profiles and tokenizer/template files. Inventory
alone is not a format or capability qualification. The local artifact manifest
pins the source GGUF model revision; independently verify its expected digests
before admitting a model campaign.

`prepare_controls.py` searches content lengths before formatting, then checks
exact token counts. It never truncates the assistant template prefix. The local
Coder template reproduces 512/2048 and historical 172/557/1069 inputs. The CLI
reports prefill for `prompt_length - 1` and includes the final prompt position
in its decode convention; these are not API TTFT or literal pp512 timings.
Use the API for common workload comparisons and recheck returned usage counts.

`benchmark_control.py` executes prepared cells against an explicitly started
loopback server, saves every request before and after execution, and reports
medians of completed per-request API rates. Start the engine with `--prompt-cache
0` for these fresh-prefill controls; reused prompts fail qualification. Each cell
receives one warmup and at least three measured requests. This is screening in
one server process, not seven independent paired confirmation blocks. Early EOS,
zero completion, token-count mismatch and absent stage timings are failed cells.
The API currently rounds stage times/rates; the harness preserves this limitation
and makes no unrounded-time or TTFT claim. A single variant's report is not a
paired speedup estimate.

Remaining instrumentation work includes request token timestamps, raw unrounded
engine stage times, owner-specific allocations/reservations, graph/MTP counters
and request-window energy. Raw tegrastats rails are retained without claiming
whole-board energy. The known multi-token raw-logit discrepancy remains an
open numerical qualification issue. Future Splash work should carry this list
of evidence gaps forward explicitly, rather than inheriting an engine's claimed
performance as a new integration result.

Models remain under `~/models/`; build products and transient evidence stay under
ignored `build/integration/`. Original Strata/NInfer checkouts are only read for
local toolchain/dependency reuse. No service or clock changes are part of this
checkpoint.

The Oct 10 Phase 3 follow-up found that this runtime namespace omits
`/proc/<pid>/io` and does not expose `io.stat` in the harness leaf cgroup.
Ancestor cgroup and whole-device block counters include unrelated work, so they
cannot be labeled as per-request storage bytes. A future Splash harness should
inventory the platform's actual process-I/O and GPU-allocation telemetry before
designing per-request accounting; Linux procfs/cgroup assumptions do not carry
over to Apple platforms.

For Orin, a temporary systemd scope with `IOAccounting=yes` did expose leaf
`io.stat`. A 64 MiB `O_DIRECT` read moved the scope's `rbytes` by exactly 64
MiB. The seven-pair mapped/pread follow-up then matched outputs and all state
fields while measuring scope reads around each request. Launching with
`systemd-run --uid` alone dropped the needed GPU device groups; a root-created
temporary scope plus `setpriv` preserved the normal user and supplementary
groups. Treat this as a Linux/Jetson measurement adapter, not a portable engine
dependency.

The [pinned H2D copy screen](../../bench/results/2026-10-10-phase3-copy-latency/README.md)
uses CUDA events around the transfer itself and retains all per-copy samples.
Its seven process medians were tightly grouped, but rare event samples were
over twice the median. A Splash transfer benchmark should preserve those tails
and time the copy separately from checksum work, allocation and request stages.

## Phase 1 continuation — Factor translation and process ownership

The paired runner uses fresh owned server processes, randomizes variant order
and workload order within three paired blocks, and warms each workload before
one measured request per process. `--expert-cache 5000` expresses a budget in
maximum-size blobs, not a promise of 5000 actual slots: the Coder profile packs
that budget into 6519 slots (12695 MiB as reported by READY). Record both the
requested budget and actual slots/bytes. MTP four is published as `mtp_max=4`
alongside a six-column native verification capacity and lookup depth three;
these counters represent different concepts.

Native-pack distribution labels also differ from element formats. Header-only
inventory of the two pinned shards finds 1224 tensors. The routed expert formats
are IQ2_S/IQ4_NL/IQ3_XXS/IQ3_S/Q2_0/IQ4_XS, despite the IQ1_M filename. Reject
codec substitution based on a model's download label. A future Splash adapter
must inventory actual tensors and preserve activation/cast boundaries in the
same way. Header geometry is not an independent element-decoding oracle.

A first campaign preserved one completed process and five failed starts because
the harness's port precheck did not allow TCP TIME_WAIT reuse. The corrected
precheck matches HTTPServer's SO_REUSEADDR behavior while rejecting a live
listener; regression tests exercise both cases. This was a harness error, not
a model or capacity failure. The rerun has a separate output directory and
per-process engine logs; failures remain auditable. Each successful API request
retains SSE chunk timestamps and first-visible-delta client TTFT, not a claim
that chunks are one token each. Metrics snapshots retain actual cache, draft,
stage and logical read counters.

First oracle preparation is documented in [operator contracts](OPERATOR_CONTRACTS.md).
The standalone diagnostic build under `tests/integration/` compiles Strata's
existing F32 weighted RMS operator against an independent FP64 oracle, with
predeclared tolerance, group/token layout, dispatch boundaries and guard checks.
It is prepared without altering production dispatch or linking the NInfer
reference. GPU execution now passes 25 numerical fixtures and eight invalid-argument cases.
Maximum relative L2 is 6.954e-8; input/gamma and output guards are preserved.
This qualifies the selected existing operator fixtures, not NInfer BF16 conversion
or whole-model parity.

## Control checkpoint — Preserve failed evidence and numerical boundaries

The successful controls comprise four independent process pairs, 40 measured
requests and 40 warmups. Three pairs have GPU/EMC observations for every measured
request window; the first missing pair remains explicit. Clock reads can require
privilege even when no setting changes. Named rails are integrated separately
with gap checks; timestamps and scope prevent a whole-board energy assertion.
SSE first-visible-delta TTFT does not require treating chunks as individual tokens.
These measurement methods transfer to Splash; Linux telemetry paths do not.

Both builds pass seven real-model protocol scenarios. Identical runtime source
still produces differing multi-token messages in several paired cells. A fresh
four-token CPU comparison agrees on argmax while retaining KL 1.302. Do not
replace an open distribution/state issue with a text-level success criterion.
Protocol recovery, operator accuracy and accepted-prefix state are separate gates.

Publication copies text evidence and plots from ignored build storage, preserves
original commands, records hashes, and keeps model payloads and compiled/logit
binaries local. Engine logs use `.txt` because the repository ignores `.log`.
No reference engine is linked into production, and no new execution route is
introduced before the remaining owner-level instrumentation gate.

## First owner diagnostic — Preserve the platform's real source route

An explicit STRATA_INTEGRATION_TRACE=1 now observes the existing verifier's
primary arena request/free and successful window graph instantiations. No second
mutable admission ledger is introduced. Requested bytes, physical backing,
graph counts and graph-pool memory remain distinct quantities. The parser fails
on duplicate ownership and unmatched releases and leaves incomplete teardown
explicit. Both trace-on/off protocol runs pass seven scenarios; only the on-run
emits the new records.

SYCL builds use migrated source copies when present, so editing only the native
owner would silently miss that backend. Its single-window finalization is
instrumented explicitly; batch coverage differences are recorded. The native
CUDA build passes; isolated HIP/SYCL validation is pending. A future Splash
integration must inspect its actual compilation route and ownership seams before
assuming that a shared-looking filename means shared execution.


## Expanded owners and reproducibility diagnostics

Owned prefill buffers and borrowed cache views need distinct events. A 512-token
prefill diagnostic borrows 192 cache slots, while its only new observed prefill
backing is the 2048-byte token buffer. Counting view sizes as allocations would
invent memory. MTP's existing payload counter includes arenas already observed;
keep it separate. These distinctions transfer to Metal heaps and Splash views.

Identical pinned Strata binary/flags produce different raw four-token logits in
two default CPU-sharing runs. With explicit STRATA_PREFILL_CPU_SHARE=0, two
pinned processes and the instrumented candidate produce identical raw logits.
This is narrow route evidence, not default-profile or whole-model parity. The
independent CPU-reference distribution still differs (KL 1.385), so bit equality
between these controls cannot close numerical qualification.

On Orin's Flash-Next path, fixed CPU/GPU prefill sharing can preserve output
tokens while changing persistent recurrence state materially: a matched 512-token
case differed by 3.172% GDN relative L2 at the first accepted boundary, and the
state fingerprints still differed after 64 generated tokens. A Splash port must
compare accepted-prefix state and later outputs when splitting operators across
CPU/GPU execution; matching short text alone does not validate recurrence
compatibility. Keep state-dump capture aligned to the measured request, since a
same-length warmup can consume a one-shot boundary hook.

Requested settings do not establish executed paths. Strata clamps KV residency
to at least 20,480 tokens: requesting 1024 with a 4096 context remains fully
resident. Save actual engine capabilities before testing and fail unsupported
cells explicitly. Configuration reservation alone does not prove context quality
or near-limit capacity.

Speculation tests must distinguish accepted drafts, the old pending anchor,
licensed outputs, output clipping and retained persistent state. Zero accepted
drafts still consume an anchor; zero published/retained tokens is a different
transaction. Map each engine's boundary before importing replay scenarios.

The Oct 11 Strata accepted-prefix test exposed a QSA indexer transaction detail
that also applies when integrating another speculative engine. Commit replay
correctly rebuilt rows for the accepted prefix, but a rejected suffix could
have completed the next four-token pooling block and overwritten the spare
pooled row. Output IDs and completed pooled rows still matched, while the full
pooled-state fingerprint differed at output clipping and could persist into a
later request. Restore the constant dead key into row
`(last_committed_position + 1) / idx_block` after replay, using the commit
buffer's accepted positions inside the existing ordered commit graph. For
Strata+Splash, map the spare/lookahead row and its invariant explicitly, then
test windows that end both before and on a block boundary. Compare committed
rows, spare rows, recurrence/KV state, output publication and a subsequent
request; final text alone will miss this class of transaction error. The
confirmed Strata fix matched every shared boundary in the 8-token MTP-off/2/3/4
screen and 32-token MTP-off/window-4 chain. See the
[raw report](../../bench/results/2026-10-11-phase5-spare-restore-long-chain/README.md).


## A codec oracle can be exact without mirroring conversion code

For IQ4_NL, half significand/exponent arithmetic and integer codebook products
are exact in FP32. An independent adjacent-value search qualifies BF16 rounding
without copying the production bit-rounding implementation. Every finite half
scale and both nibble halves pass, plus real expert matrix dimensions with
synthetic payloads. Keep a format's mandated table as format data; do not import
an implementation helper into its oracle. This method transfers to Splash,
while CUDA launch and guard mechanics require a Metal-specific diagnostic.


## Projection roles do not imply parent or head layout compatibility

The checked Flash-Next map rejects all 48 layers against the chosen pinned
NInfer two-parent profiles. GDN uses QKV and gate/Z parents; QSA interleaves
query/gate per head, which a naive contiguous split would corrupt. Always record
logical dimensions and physical arrangement separately, and distinguish source
codec headers from prepared runtime planes. A future Strata/Splash seam map
should retain symbol-specific incompatibilities and explicit failed-profile
cells before introducing rearrangement or conversion adapters.


## Cache and workspace admission must use executed values

The Orin cache/context screen requested 3000 and 5000 expert slots but the
runtime selected 3903 and 6519; those request values are sizing lower bounds,
not exact capacities. With automatic sizing, owned prompt buffers emitted
separate workspace holds (202, 500, 840 and 1520 MiB for chunks 64, 512, 1024
and 2048), while borrowed buffers emitted no such hold. The existing 3 GiB
VRAM slack and MTP bind hold remained distinct. Report requested settings,
actual capabilities, reservation metadata, observed owner allocations and
physical `MemAvailable` separately. A reservation event is not an allocation,
and GPU free-memory telemetry must not be added to host availability on a
unified-memory device.

For a future Strata + Splash integration, preserve this experimental shape but
replace CUDA-specific observations with the actual Metal allocator and resource
residency APIs Splash uses. Determine whether a configured prompt chunk owns
buffers or borrows from a cache, query the executed cache capacity, and record
any future workspace budget separately from committed allocations. Use one
physical-memory authority for Apple unified memory, retain headroom, and sample
the OS while supervising each process. A short prompt can verify startup and
admission but cannot establish behavior at the configured chunk size; prepare a
prompt that reaches the intended boundary before testing full-chunk workspace
pressure.


## Measure materialization and preserve profiler scope

The pinned pp512+tg64 trace ranks Q6_K→FP16 materialization above individual
compute kernels by summed GPU duration. Format conversion can be a meaningful
cost even when the contraction kernel is fast. Reuse versus caching decisions
must include unique backing, lifetime and request benefit under the physical
floor. Kernel sums include concurrent streams and spin waits; startup library
loads and allocations remain outside request-cost claims. Approximate UTC
window alignment needs explicit sensitivity and uncertainty; future Splash
profiling needs its own trace-clock and request markers, not Linux timestamps
assumed to transfer unchanged.


## Pinned host staging is an owner-specific experiment

`STRATA_STAGE_PIN=1` does not exercise the expert-stage pool by itself. On this
file-backed route, `STRATA_IO_PREFETCH=1` with `STRATA_IO_PF_STAGE=1` selects the
staged I/O path; the ordinary prefetch mode only fills the page cache. Trace
pinned and pageable host buffers as separate owners, and emit a pinned free only
after the runtime reports successful release. These bytes belong to host RAM,
even when the CUDA API allocated them. Two three-pair 4K-prompt Orin screens
matched tokens and committed state. The trace-corrected repeat showed a 0.10%
median prompt regression and variable decode deltas from -9.24% to +3.94%; this
does not establish a benefit, so pinning remains opt-in. Splash will need its
own resource class and lifetime instrumentation; pinned CUDA semantics do not
transfer to Metal.

An additional exact 512-token/64-output Orin screen paired mapped expert reads
with whole-blob `pread`, with staging disabled in both arms. All three pairs
matched tokens and persistent state. The mapped arm had a 22.7% lower decode
median but a 1.7% higher prompt median; process major faults were lower for
pread. Disk-byte and copy-latency counters were unavailable, so the result is
screening evidence only. For Splash, preserve the measurement dimensions and
state/checksum controls, then measure Metal-specific read, copy and residency
counters rather than translating CUDA owner labels.

The Oct 10 follow-up added request-local file-tier bytes and summed pread-worker
time, with deltas seeded after model/cache startup. On three exact 512/64 pairs,
mapped and pread outputs and persistent state matched; both handed out 40,996.1
MB of expert reads per request, while pread workers read 2,216–2,298 MB and
spent 2,516–2,723 ms cumulatively. The mapped path reported page-cache
residency; the pread/fill-cache path does not sample it, so its log omits those
fields instead of reporting false zeroes. `/proc/self/io` bytes are unavailable
on this Orin kernel, and whole-device counters include unrelated reads and
readahead. For Splash, keep request-local transfer counters distinct from
device-level storage traffic, state whether worker time is summed or wall time,
and establish counter baselines after loading/warmup. The full protocol and
limits are recorded in the [transfer telemetry report](../../bench/results/2026-10-10-phase3-transfer-telemetry/README.md).

An opt-in `tegrastats` sampler integrates each named system rail over a request
and records available CPU/GPU/EMC clocks. On this Orin, CPU frequencies and rail
power were available, while GPU/EMC frequencies were absent. Auto-cache
diagnostics selected different expert capacities between processes and showed
state mismatches; fixed `--expert-cache 5000` restored exact token/state parity
for both an MTP-off one-token repeat and all three `spec4` mapped/pread pairs.
For Splash, keep cache residency fixed within every pair and retain the actual
capacity and hits alongside state hashes. Rail values include unrelated system
activity and are not additive or process-attributed. The [failed auto-cache
diagnostics](../../bench/results/2026-10-10-phase3-transfer-energy/README.md)
and [fixed-cache transfer screen](../../bench/results/2026-10-10-phase3-transfer-energy-fixed-cache/README.md)
preserve the comparison and its limits.

A seven-pair randomized fixed-cache follow-up measured mapped request time
4.14% lower at the median for the same 512+64 workload, with a bootstrap
interval for the median paired delta of −5.57% to −4.02%. All outputs and nine
state fingerprints matched, and the six-GiB headroom floor held. Prompt times
were nearly equal while decode favored mapped reads. The estimated system rails
and NVMe partition counters include unrelated work, so this remains one-device,
one-workload evidence and does not justify changing a default. In a future
Strata + Splash study, pair file/resource access paths with fixed residency,
identical state and emission checks, and separate Metal resource residency from
system-wide memory pressure. Keep device I/O and power counters labeled by scope;
do not convert host-wide observations into process-level claims. See the
[seven-pair report](../../bench/results/2026-10-10-phase3-transfer-confirmation7/README.md).

The [async-pool transfer screen](../../bench/results/2026-10-10-phase3-async-pool/README.md)
adds a 64 MiB transient CUDA pool allocation/copy/kernel/free path beside pinned
copy, mapped-host and sequential-managed controls. It checks exact checksums,
records the 64 MiB pool high-water and verifies zero live pool bytes afterward.
The transient async path's one-run median was slower than the persistent-copy
control, so no path is promoted. For Splash, keep async allocation lifetime and
reserved-versus-live bytes separate from Metal residency, and compare a
transient path only with controls that share its allocation lifetime.

The 3,522-token/256-output Orin recovery smoke then served a separate short
request through the same engine. It passed above the six-GiB floor, while
workspace and cache owners remained service-resident until orderly shutdown.
For Splash, distinguish service-lifetime reservations from per-request scratch
and prove recovery by serving the follow-up request; teardown balance alone
does not prove a request released reusable workspace.

## Separate virtual address ranges from physical backing

The segmented CUDA expert cache reserves one address range and maps physical
segments into it. Trace the physical handle only after mapping succeeds, and
close its observed lifetime only after unmap and release succeed; the reserved
address range is not backing memory. The Orin test shrank and regrew both
uniform and sized caches while checking retained slot bytes and matching each
observed allocation with a free. A future Splash adapter should apply the same
identity distinction to Metal heaps, sparse resources and aliases, while
tracking Metal-specific residency and shared backing semantics. Shared CUDA
VMM chunks now have a global physical-handle lifetime that remains live while a
chunk moves between expert-cache and K/V ranges. Each map/unmap is also recorded
against its range instance without adding the mapped view to backing totals.
Range instance IDs still need semantic role labels for easier attribution, and
other CUDA/driver allocations remain outside this partial owner ledger.

The candidate's optional CUDA vision path also needs a separate process/memory
scope: the Python service launches `strata-vision` with the projector, then
forwards its embeddings to the model engine. A fresh 56×56 image request passed
on Orin above the six-GiB floor, but the engine owner trace did not include the
encoder process or graph-pool bytes. A Splash port should record image decode,
Metal encoder allocations, embedding lifetime and model-side image buffers as
separate owners, then validate the total with system memory-pressure telemetry.
An Oct 10 process-tagged CUDA runtime probe attributed 871.4 MiB of tracked
allocation high-water to the encoder PID and 17.72 GiB to the separate engine
PID during a passing image request. These API ledgers are lower bounds and must
not be added to each other or host RAM; driver/internal and graph-executable
allocations are not fully observed. For Splash, tag allocations by process and
resource lifetime while using unified physical pressure as the admission
authority.

CUDA's graph memory attributes report the asynchronous graph allocator; a
calibration with graph allocation nodes confirmed those values, while Strata's
captured kernel graphs used none of that pool. The API therefore cannot stand
in for total graph executable residency. For Splash, track command-buffer
lifetimes and Metal heap/resource residency at each capture/replay boundary,
including driver-managed transient memory; report API-specific counters beside
system-wide physical pressure rather than treating a zero pool reading as zero
graph cost.



## Keep source quantization separate from materialized dtype

Q6_K diagnostic fixtures derive expected outputs from logical signed values,
subscales and half scale, then compare native F32/BF16/FP16 paths. The BF16 and
FP16 outputs each have distinct exact rounding contracts; equality of their
weight encodings or shared source storage says nothing about model-quality
interchangeability. Exhaustive storage conversion is not a substitute for a
real-layer accuracy and state test. A future Splash/Metal port should preserve
both format identity and output dtype at this seam.

For the profiled Q6_K materializer, qualify the exact runtime entry point on
real payloads and the observed full matrix shapes before testing alternate
schedules. The Orin diagnostic first checked output bits on real rows, then
timed full device-resident matrices in shuffled shape-order blocks, reporting
source-plus-destination traffic as nominal effective GB/s. Its timing excludes
model loading and the initial copy and uses warmed repeated inputs; this makes
it an operator baseline, not a production transfer or end-to-end result. For
Splash, preserve these boundaries while measuring Metal resource residency,
actual clocks and system-wide physical pressure with the backend-specific
profiling permission model documented.

The Q6_K test-only CTA-size screen compared 128/256/512 threads with the
production 256-thread path over full real matrices and required bitwise output
equality before timing. Its three process-level repeats found no consistent
winner; profile-weighted changes were sub-percent, and the 256/512-thread
effects crossed zero between processes. This is a rejected local schedule
screen, not a reason to alter the default. For Splash, vary a threadgroup
parameter only after the source decode and output contract is fixed, randomize
schedule order, and repeat separate processes before deciding whether a
candidate deserves service-level testing.

## Make parity readers artifact-aware at the PLE seam

The fixture-free block oracle from Strata upstream PR #568 avoids captures
that were never included in the repository, but its initial reader is tied to
one pack representation: separated 2-bit key codes and FP16 group scales plus
a 32-bit-expanded BF16 value tensor. The downloaded GSQ-RCO Q2_0 artifact keeps
the key in native GGUF Q2_0 blocks and stores the value directly as BF16. The
diagnostic now adapts this Q2_0 source directly: it validates the GGUF tensor
name, shape, type, bounds and payload size, separates the 64-code Q2_0 blocks
into the oracle's code/scale view without changing represented values, and
accepts the pack's raw BF16 value bits and verifies they match the source GGUF
value tensor byte for byte. It also reassembles the exact source Q2_0 blocks
and requires byte identity before checking the native projection.
The CPU reference applies the Q2_0 `(code - 1) * fp16_scale` equation and the
kernel's Q8_0 key activation / BF16 value activation contracts. All seven PLE
stages are checked against real gathered table rows and real layer-1 weights;
the native Q2_0 key projection is compared against the independently decoded
key path. This is a block-level oracle with synthetic hidden state and
convolution history, not whole-model quality evidence.

For a future Strata + Splash integration, retain source-format identities and
build an adapter from the source metadata and pack index, then compare the
source-format decode oracle against the backend's actual materialized weights.
Do not fix a failed fixture lookup by substituting a tensor from a different
model cohort; tensor shapes alone do not establish matching values.

## Treat worker-count results as correctness-gated experiments

Orin Nsight Systems CPU instruction sampling found many samples in the expert
pool worker loop during a `pp512+tg64` API request. A randomized fixed-workload
screen showed lower median times at eight workers than at eleven, but the
screen's gate failed: one of three eleven-worker outputs differed, and exact
persistent-state fingerprints differed across every worker configuration.
Those timings are not a worker-count speedup result. Before repeating this on
Strata or Splash, record token IDs and accepted-prefix state at verifier commit
boundaries, then require correctness across worker settings before comparing
latency. For Splash, also record which CPU or GPU owns each expert operation;
worker count may change CPU/GPU contention for shared memory bandwidth even if
the operator sequence is unchanged.

The experiment harness accepts a separate warmup workload set so the measured
prompt can remain a fresh prefill while still warming model and service state.
Use distinct prompts with identical token counts and chat-template settings,
and confirm `cache_n=0` on measured requests. Retain the failed initial setup
where warmup repeated the measured prompt: that was a harness failure, not
evidence about the runtime.

Accepted-prefix hashes locate recurrent-state differences but do not quantify
their size. For a long-prompt prefill-chunk comparison, the Orin harness now
supports an explicitly requested one-time float32 GDN dump at a selected
accepted length (`STRATA_STATE_DUMP_GDN` plus `STRATA_STATE_DUMP_GDN_AT`). Use a
distinct shorter warmup so the selected length identifies the measured request,
retain the binary checksum and a compact numeric summary, and keep the large
dump itself outside Git. At `L=1069`, chunk 32 versus 128 changed 98.37% of GDN
values with 3.138% relative L2 despite matching output IDs. This establishes a
state difference, not which state is more accurate. A future Strata + Splash
effort should adapt the dump to the actual recurrent-state layout and use an
independent mathematical or task-level oracle before judging either state.

The actual Q2_0 native-model admission matrix adds a related portability lesson:
cache budgets and context reservations need to be measured on the target model
artifacts, even when an IQ1_M screen already exists. On Orin, the Q2_0 3,000- and
5,000-slot cells reported 3.86 and 6.44 GiB of shared-RAM cache backing, while
doubling context added 108,068,864 requested session bytes. Splash should run
the same model-specific matrix against its Metal-backed owner and report host
availability, device requests and virtual reservations as separate quantities.
Orin also passed the Q2_0 512-token/one-output request under 10/12/20/24 GiB
cgroup caps. With the same 3,000-slot request, the runtime admitted 296 and 805
actual slots under 10/12 GiB, then 3,000 under 20/24 GiB. At 8 GiB, zero
slots were admitted and the speculative route failed after prefill with 6.74 GiB
effective and 22.31 GiB host availability. The tightest passing cell retained
6.99 GiB effective and 21.57 GiB host availability. A future port should test
its actual constrained service scope while preserving the platform-level
physical headroom guard; a cap-only success does not establish general model
capacity.

For transfer modes, compare the operator-specific counter with whole-request
time and keep allocation tracing out of timing arms. The Q2_0 PLE mmap/direct
screen returned a 0.3 ms PLE counter inside roughly 14 s prompts; a tracing-off
three-pair follow-up had opposite paired directions and a 0.49% median prompt
difference. It does not justify a PLE I/O policy change. Splash should expose
the corresponding Metal operator/copy counter before interpreting end-to-end
timing, and retain an explicitly unsupported result if that counter is absent.

A 256-slot Q2_0 cache request failed at 8 and 9 GiB cgroup caps (zero slots), then passed at 9.5 and 10 GiB with the same request, model, prompt and runtime settings. This brackets the observed transition for that one configuration between 9 and 9.5 GiB; it is not a general support threshold. The 10 GiB/3,000-slot request separately contracted to 296 actual slots. For a future Strata + Splash port, log requested budget, actual resident slots, admission reason and workload together; do not extrapolate a support threshold from cap size alone.

The Q2_0 artifact-aware PLE oracle also passes inside a 10 GiB cgroup scope, with all seven stages checked for three tokens and the real native key reconstructed byte-for-byte. The 32.1 MiB scope peak is specific to the short operator test; it does not price full-model service memory. For Splash, test correctness fixtures inside a constrained scope separately from full-runtime admission, and do not treat a small fixture's cgroup peak as a serving estimate.


A second graph-memory probe wrapped both the CUDA runtime instantiate call and public Driver allocation APIs. The direct Driver allocation/free calibration was visible, but the real service's 10 graph instantiations produced no interposable Driver allocation events. A later root-readable NVMap IOVMM client trace, calibrated against a live 512 MiB CUDA allocation, measured the same 83,427,328-byte process-owner increase across ten graph-instantiation calls in each of three IQ1_M service startups. This is a measured capture/instantiate interval for that setup, not a universal executable size or graph-disabled differential. For Splash, validate instrumentation against the exact native graph-creation path, and treat absent allocator events as unknown until an independent heap or system-pressure delta can bound them.


The one-token Q2_0 cache-cap bracket does not predict longer-generation admission: at 256 slots, 64-token requests were aborted under 9.5, 10 and 12 GiB scopes before prefill, and at 16 GiB after prefill; 18 and 20 GiB cells completed. Effective cgroup availability, including file-cache charge, must be sampled during the request. Keep prompt/generation length and actual admitted cache slots in every support cell on a future Strata + Splash port.

## Compare heterogeneous CPU/GPU prefill by committed state

The automatic CPU/GPU prefill-sharing policy was not repeatable on Orin in a
matched three-process test, even though all eight output tokens and accepted
token IDs matched: full recurrent-state hashes differed at the first recorded
verifier commit and every later boundary. Fixed 0.5 sharing and disabled sharing
were each repeatable across three processes when actual expert-cache capacity
was held at 3,903 slots, but the two policies produced different committed
states. This points to a policy-dependent numerical path, not an accuracy result;
tracing also synchronizes, so these runs do not qualify timing. A Splash port
should record exact source tensors, cache residency, CPU/GPU work assignment,
accepted IDs and full committed recurrent/KV state under matched capacity before
using output text or latency to judge a split policy. Re-run with an independent
operator or task-level oracle to decide which policy is accurate.

## Calibrate physical-memory counters before pricing GPU allocations

An Orin visibility calibration successfully allocated and touched 512 MiB
through CUDA, but `cuMemGetInfo`, host availability, the interactive cgroup
counter and `tegrastats` did not show a commensurate change. The root-readable
NVMap IOVMM client table did: its per-process total rose by exactly 512 MiB and
returned to baseline after free. The three-process graph follow-up measured an
83,427,328-byte net process-owner increase across ten graph-instantiation calls
in each service startup. This is an interval cost for that IQ1_M configuration. A separate Q2_0 spec2
measurement found the same 72,425,472-byte stable-to-stable increase in three
processes through four successful runtime graph-instantiation calls. That run
exposed a missing verifier-commit graph owner event, now instrumented and checked
against all four runtime calls. Both NVMap results include adjacent synchronous
allocations and are configuration-specific intervals; they are not graph-executable
sizes. Other graph paths and non-NVMap allocations remain unpriced. For Splash,
calibrate each Metal and OS memory counter against a known live allocation
before using it to price graph, heap or residency costs, and retain an unpriced
status when the calibration fails.

The supervisor now records cgroup-v2 `memory.stat` byte counters and
`memory.events` alongside `memory.current`. In a Q2_0 64-token retry at a
20 GiB cap, one process safely aborted at the six-GiB cgroup headroom guard
while host availability stayed above 21.9 GiB; two later processes completed
with identical 64-token IDs. The passing detailed sample had 8.29 GB file cache
and 1.63 GB anonymous charge, with no max/OOM events. For Splash, retain
file-backed cache, anonymous use and system physical headroom separately; a
cgroup success/failure pair should be treated as an observation of that scope
and run history, not a device capacity threshold.

The follow-up [IQ1_M MTP graph-owner trace](../../bench/results/2026-10-11-phase3-iq1-graph-owner-check-rerun/README.md)
labels successful MTP device-prefill, round and step graph instantiations in
both CUDA/HIP and SYCL code. In one spec4 service sequence, the ten runtime
instantiation calls matched ten owner events (three verifier windows, one
verifier commit, and six MTP graphs); the API/cancellation/recovery scenarios
passed above the six-GiB host floor. This is graph-call attribution coverage,
not graph-pool sizing or total memory ownership. A future Strata + Splash port
should inventory each engine's graph creation sites, attach labels only after
successful instantiation, and compare the count with an independent runtime
probe. Keep the calibration and workload/configuration identity with any
platform memory delta. A later [session-graph instrumentation follow-up](../../bench/results/2026-10-11-phase3-graph-session-owner-check/README.md) adds events at legacy per-layer session graphs, the session token graph, and the generic `CapturedGraph` registry in CUDA/HIP and SYCL. The validated native pack bypasses those legacy paths, so its seven-scenario Orin rerun only confirms the verifier/MTP sequence remains 10/10; session-graph runtime coverage remains untested. For Splash, include these graph families in the owner inventory but keep unexercised classes separate from runtime-qualified evidence.

The [Oct 11 current-checkout rerun](../../bench/results/2026-10-11-phase3-ple-rerun/README.md) reconfirmed the artifact-aware Q2_0 PLE oracle and the 15-test accounting/owner suite under the six-GiB supervisor. Keep this kind of rerun split into an independent real-artifact operator oracle and focused ownership contracts; a passing oracle with synthetic hidden/history inputs must not be presented as serving quality or full-runtime memory evidence.

The [same-day pageable/pinned stage check](../../bench/results/2026-10-11-phase3-stage-pin-confirm512/README.md) matched output IDs and full persistent state across both staging choices, while requested host backing varied by arm and a decode outlier overwhelmed the timing sample. For a future Splash port, preserve per-arm owner byte counts and state parity, but require stable copy counters and clocked, paired end-to-end repeats before drawing a transfer-performance conclusion.

The companion [traced owner/state check](../../bench/results/2026-10-11-phase3-stage-pin-state2048/README.md) at the same prompt and output length matched all nine state fields and balanced each arm's owner lifecycle, while reporting pinned/pageable requested staging bytes separately. Carry the same split into Splash: traced correctness and untraced timing need distinct runs, and owner payloads must not be presented as physical backing.

The held-out [2,048-token pageable/pinned timing confirmation](../../bench/results/2026-10-11-phase3-stage-pin-timing2048/README.md) adds seven trace-free pairs. It preserved generated IDs and actual cache capacity, but did not hash state; prompt and total-request intervals included zero and decode was highly variable. For Splash, keep held-out timing paired and instrumentation-free, yet retain a separate state/owner diagnostic; do not use matching text or a noisy decode interval to justify a default.

The first [no-trace worker-count screen](../../bench/results/2026-10-11-phase4-pool-workers-512-no-trace/README.md) measured 1/2/4/8 ARM CPU workers with a fixed 3,903-slot cache and CPU prefill sharing disabled. Eight workers were fastest in all three blocks, but the single 512-token/eight-output workload, unlocked clocks and absent GPU/EMC frequencies limit the result to screening. For Splash, define workers by the actual CPU/GPU scheduling boundary and repeat across held-out prompt lengths; do not copy Strata's count as a preset.

The [1,069-token follow-up](../../bench/results/2026-10-11-phase4-pool-workers-1069-no-trace/README.md) repeated the 1/4/8-worker ordering with smaller differences: eight workers led four by 1.01–1.60% in request time, compared with 1.76–2.84% on 512 tokens. This is one observed worker × prompt-length interaction, with output/cache checks only and unlocked clocks; a future Splash campaign should include prompt length as an interaction factor and measure committed state in its correctness arms.

The paired [accepted-prefix follow-up](../../bench/results/2026-10-11-phase4-pool-workers-1069-state/README.md) then confirmed all token commits and persistent state across those worker counts on the held-out prompt. Keep this state check separate from timing: the trace synchronizes execution. For Splash, compare committed state across scheduling choices on longer prompts before using output hash parity as a proxy.

The extra Q2_0 repeat at a 20 GiB cgroup cap stopped safely at 5.55 GiB scoped headroom while host availability remained 20.90 GiB and OOM counters stayed zero. Together with earlier passes and aborts, this shows why a container limit alone cannot stand in for a stable admission result. For Splash, log platform physical availability and each effective cgroup ancestor, plus file/anonymous charge where available; retain pressure-aborted attempts as outcomes.

The [Q2_0 cancellation-under-pressure and owner cleanup checks](../../bench/results/2026-10-11-phase3-q2-cancel-recovery-22G/README.md) reinforce two reusable rules: report a cgroup pressure abort separately from host physical pressure, and make diagnostic-buffer cleanup scope-bound so errors after allocation still balance the owner trace. The 18 GiB cell crossed the six-GiB cgroup guard and was supervisor-aborted; at 22 GiB, cancellation after 512/2,048 prompt tokens and same-process recovery passed with all 302 allocation/free pairs balanced. A separate [layer-dump owner check](../../bench/results/2026-10-11-phase3-layer-dump-owner/README.md) confirmed that the 2,007,040-byte pinned debug buffer is released on the verifier's unsupported-configuration return, although successful dumping is not available on this native speculative route. For Splash, instrument any debug-only pinned or mapped buffers, test early errors as well as successful teardown, and keep platform-wide physical memory distinct from process or cgroup caps.

## Trace every MTP backing allocation, including logits

The MTP owner ledger initially covered state and scratch arenas plus copied
weights, but omitted the draft logits buffer allocated during `bind()`. Add the
owner event at the successful native allocation, retain the exact requested byte
count, and emit release only after a successful free. Verify a traced model run
through cancellation and orderly shutdown; the Oct 11 IQ1_M/MTP check balanced
53 allocation/free events with zero live bytes and 9.84 GiB minimum host
availability. Keep the existing payload snapshot separate because it overlaps
observed backing. For Splash, inventory temporary logits and sampling buffers as
well as persistent weights and state, and do not sum payload snapshots with
unique live allocations.

## Separate transfer correctness traces from transfer timing

On Orin, the pageable/pinned stage trace matched output IDs and persistent state,
but its tracing overhead made timing descriptive. A separate seven-pair
trace-free screen retained equal output IDs and fixed actual cache capacity,
then measured prompt/decode stages with pair-level bootstrap intervals. Its
uncertainty was wide and did not support a pinned-stage benefit. For a future
Strata + Splash comparison, first qualify output/state and owner lifetimes in a
traced diagnostic, then collect timing with all instrumentation disabled and
report its own per-arm buffer/copy counters separately. Do not combine the two
runs or use request text alone as a state-parity check.

The configured-context × speculation graph screen now has Q2_0 observations at
32K for spec2 and spec4. At spec4, three Driver instantiate calls matched three
owner events, with a 48.71 MB stable NVMap interval; spec2 had four calls and a
72.43 MB interval. These are configuration-specific capture intervals, not
per-graph executable costs. For Splash, vary context and graph/speculation shape
as separate factors, calibrate the platform counter, and retain actual request
length so a configured reservation is not presented as long-context execution.

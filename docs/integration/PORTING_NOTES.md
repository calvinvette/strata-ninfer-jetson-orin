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
| Attribute weight arenas | Main CUDA `WeightTable` dense arena is one explicit allocation with an opt-in owner event; do not count its suballocated tensor views again | Inventory each dense/packed arena and its lifetime; distinguish backing allocations from tensor views and confirm successful free events |
| Attribute helper-process allocations | `cuda_alloc_observations.py` groups a test interposer's runtime allocation events by PID; pair it with the owner event ledger and whole-board MemAvailable | Instrument the encoder/helper process as well as the engine; keep process request totals separate from physical capacity and from each other |
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

For the 1,024-token Orin vision smoke, a test-only CUDA runtime interposer
observed the vision encoder and Strata engine as separate PIDs. The
`tools/integration/cuda_alloc_observations.py` parser retains per-process
high-water and shutdown-current request counts. This supplements the Strata
owner trace, which cannot account for a separate executable. The interposer
observes selected CUDA runtime allocation calls only: it does not measure
driver-private, graph-pool, or unique physical backing, and its process totals
must not be summed as if they were separate memory pools. The authoritative
admission check remains whole-board MemAvailable under the six-GiB floor. See
the [vision attribution rerun](../../bench/results/2026-10-12-phase3-vision-1024/README.md).

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
CUDA build passes; isolated HIP/SYCL validation was pending at the time of this
note. A future Splash integration must inspect its actual compilation route
and ownership seams before assuming that a shared-looking filename means
shared execution.

The pending backend check has since been completed on maestro1 from a clean
snapshot of the current integration revision: full single-job HIP and SYCL
compile/link builds passed. These remain x86 build checks, not accelerator
runtime evidence. The report retains toolchain identities, source checksums,
binary hashes and build logs for future Strata/Splash parity work. See the
[Phase 8 backend report](../../bench/results/2026-10-14-phase8-maestro1-4b72a72/README.md).


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
At a 32K prompt, changing Q2_0 cache capacity from 3,000 to 5,000 preserved
the emitted token but changed 94.32% of 29.4 million GDN floats; whole-state
relative L2 was 4.687%, with material drift first at layer 3. Repeat state
checks at fixed capacities and measure cross-capacity drift numerically. For
Splash, compare against an independent state/quality oracle before choosing a
capacity, since output text alone does not identify the more accurate result.

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

The `SessionLoopScratch` owner check adds a direct 64-KiB mapped/pinned host-buffer lifecycle test. Its opt-in trace records one allocate/free pair, and repeated teardown emits no duplicate release. For Splash, attach accounting to the existing owner and test its lifecycle directly when the full legacy model route is unavailable; keep that separate from a model-route claim.

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

The Q2_0 native pack has no `experts.bin`; its expert tensors come from a GGUF
shard. The transfer harness therefore accepts an explicit model artifact to
identify the backing block device. The resulting block-sector counter is still
whole-device and includes unrelated reads; process and cgroup counters must be
reported separately when available. For Splash, keep filesystem selection
independent from the engine's model-format assumptions and calibrate the
counter scope. A Q2_0 worker/read-policy matrix also had one intermediate and
final state-fingerprint mismatch despite identical generated IDs; three fixed
worker/mapped repeats passed, but did not explain it. Preserve the failed
cross-cell state trace and require committed-state parity before timing a
transfer/scheduling factorial.

The configured-context × speculation graph screen now has Q2_0 observations at
32K for spec2 and spec4. At spec4, three Driver instantiate calls matched three
owner events, with a 48.71 MB stable NVMap interval; spec2 had four calls and a
72.43 MB interval. These are configuration-specific capture intervals, not
per-graph executable costs. For Splash, vary context and graph/speculation shape
as separate factors, calibrate the platform counter, and retain actual request
length so a configured reservation is not presented as long-context execution.
Three actual 32,768-token requests at 64K configured context and spec2 each
recorded four owner-matched instantiations and the same 71,983,104-byte (68.65
MiB) NVMap increase across the first-to-fourth graph interval. The long prompt
extends the measured workload shape and the interval repeated across processes,
but it still contains adjacent allocations; Splash should add graph-disabled
controls before attributing a platform-memory delta to graph pools.

## Bounded vision admission and per-process ownership

The 16-token vision smoke only qualifies a low-token image request. On Orin,
add explicit min/max token limits to the reproducible smoke harness and run a
large fixture under the ordinary six-GiB physical-memory supervisor. A 2,048²
synthetic fixture at a 1,024-token cap completed at 7.005 GiB minimum host
availability; an interposed repeat separately observed a 989.5 MiB vision
process CUDA runtime peak and 8.606 GiB minimum availability. Treat these as
bounded points with limited evidence, not a general vision admission guarantee.
Keep `strata-vision`'s process-specific allocation probe separate from the
engine owner trace, and state its blind spots: CUDA runtime calls do not cover
driver, graph, or vendor-internal backing. Future Splash work should capture
both process lifetimes and system-wide physical availability without summing
those ledgers.

A model-free Orin self-test confirms managed sequential ownership only when the
CPU/GPU handoff is synchronized; it does not claim concurrent managed access.
The same test separately validates mapped pinned-host publication with
platform acquire/release operations and a 2-MiB CUDA VMM mapping cycle. For a
future Strata + Splash port, keep these primitives separate from product
buffer qualification: test the actual buffer's ownership transitions, lifetime,
physical backing and end-to-end effect before selecting a transfer mode.

The Orin memory self-test now also exercises `cudaMallocAsync`/`cudaFreeAsync`
on one stream, verifies the GPU result, and trims the default pool back to its
zero-byte baseline. This proves that the primitive is available and the tested
allocation can be released. Before using stream-ordered pools for an engine
buffer, measure allocator latency, pool retention under concurrency, RAM
headroom, and request-level impact against the existing allocator.

## Separate configured reservations from work actually exercised

The current Q2_0 admission screen crosses 3,000/5,000 requested expert slots
with 4K, 8K, 16K, 32K and 64K configured context. The added 16K/32K/64K cells
each used a 512-token prompt and one output token. Session and owner requested
bytes rose with the configured context, and all cells stayed above the six-GiB
host floor, but none is a long-context request or supported-capacity result.
For a future Splash port, record the configured reservation and actual prompt
length as separate axes; use a real long prompt before claiming execution at
that context.

The current-binary cgroup recheck also produced a state-dependent result: the
8/10/12/14-GiB scopes hit the six-GiB effective cgroup guard, while 16 GiB
completed one 512/1 request. Host `MemAvailable` stayed high in the stopped
cells and no OOM event occurred. Earlier 10/12-GiB runs had passed under a
different charged-cache state. For Splash, calibrate the cgroup availability
policy against reclaimable file pages and retain every pressure abort; a
successful or failed cap is one observation, not a minimum device-memory
requirement.

At 64K/spec4, three fresh Q2_0 service starts each matched three successful
graph instantiations to owner events. Calibrated NVMap client backing increased
by the same 48,709,632 bytes in all runs, equal to the measured 32K/spec4
interval. The interval includes adjacent synchronous allocations, so it does
not price graph executables or prove context-independent graph memory. A
future Metal/OS counter should be calibrated, sampled around stable pre/post
plateaus, and tied to instantiation events; report platform-owner deltas
separately from the engine's unique requested-allocation ledger.


## Phase 3 continuation — Allocation refusal and retry evidence

A current Q2_0 candidate repeated the injected automatic expert-cache allocation
refusal in three fresh Orin processes at the same configured context and request
shape. All three retried at smaller capacities, returned the expected token and
balanced the instrumented allocation ledger. The admitted slot count changed
with available shared memory at retry time, so record both the initial request
and chosen fallback; never turn one fallback size into a general capacity limit.
For a future Strata + Splash port, exercise the allocator's refusal path with
its native physical-memory guard, retain failure and retry telemetry separately,
and verify same-process or process-restart recovery according to that engine's
service architecture. A simulated refusal does not establish behavior under a
real Metal allocation failure.

The Oct 12 Q2_0 cache-capacity diagnostic found bit-identical first logits and
repeatable GDN state within each 3,000- or 5,000-slot setting, but different
logits and accepted-prefix state across settings despite the same prompt and
selected token. For a future Strata + Splash integration, pair cache/allocation
profiles with exact prompt token IDs, repeat each profile independently, and
compare output IDs, raw logits and persistent-state tensors. Matching text or
argmax alone is not a state-parity check. Retain raw dumps outside Git with
hashes and record the first state layer or operator that diverges; do not
promote a profile until its numerical and task-level effects are understood.
An opt-in CPU-order reduction toggle left these two capacity-specific state
dumps byte-identical to their default-path controls, so that arithmetic order
toggle alone did not account for the capacity effect. For Splash, test such
debug toggles with raw state equality and retain negative results; a plausible
mechanism is not a diagnosis until an intervention changes the observed effect.
The 16-cell Q2_0 screen further found repeatable accepted-prefix GDN changes
across both prefill chunks (64/128/256/512) and cache capacities (3,000/5,000),
while a one-token output stayed the same. For Splash, cross these two resource
factors in the same prompt-prefix experiment and compare raw recurrent state;
validate longer task output separately before deciding whether the deltas fit
the numerical contract.
Record the corresponding unique owner requests beside OS-level available
memory and platform counters. Do not treat an owner ledger as a physical-memory
total when driver or graph backing is outside its instrumentation.
The Q2_0 continuation check also held the same 64-token output sequence across
the tested profiles while accepted-prefix fingerprints differed at every
commit. For Splash, include a fixed greedy continuation and compare every
published prefix; equal text alone does not prove recurrence-state parity, and
different fingerprints still need a separate task-level quality criterion.
When measuring prefill chunk performance, keep timing arms trace-free and pair
them with separately traced state/owner diagnostics on the exact same prompt
and factors. On this Orin screen chunk 512 improved median client elapsed over
chunk 64, but accepted-prefix states differed; the timing result cannot qualify
chunk 512 as a safe default. Reproduce both checks independently for Splash.

The Oct 12 automatic-cache follow-up reconciled the engine's planned
prefill-workspace hold with the unique requested-allocation peak of that owner
on one real Q2_0 request: a 500 MiB hold covered a 333.8 MiB peak, while the
separate 3 GiB workspace slack remained distinct. For Splash, preserve the
planned-versus-materialized distinction, attribute each materialized allocation
to one owner, and compare the owner ledger with platform physical-memory
telemetry. A planned hold is metadata, not backing, and an owner request peak
does not price allocator or driver overhead.

The randomized three-process-per-cell Q2_0 cache × context screen found that a
64K context added 1.41 GiB to the session owner while automatic cache allocation
fell by 1.37 GiB; the combined unique device-request peak differed by 44.3 MiB
between 8K and 64K. Output IDs matched, but this was an admission experiment,
not a quality or speed comparison. For Splash, cross configured context with
automatic cache sizing using fresh processes, preserve each chosen cache size
and reservation, and report the complete owner peak beside platform telemetry.

## Phase 4 continuation — Held-out kernel confirmation

The opt-in Q6_K warp-layout path reduced request time in seven paired 8K-context
processes for both 512/64 and 2,048/128 workloads, with each pair matching text,
speculative draft/accept counts and actual cache capacity. The paired benefit
came from prompt processing; decode effects were small and mixed. The result
does not establish task quality or justify changing dispatch. For a future
Strata + Splash comparison, keep kernel selection opt-in while collecting
matched formatted prompts, per-stage timings, output identity, cache capacity,
platform clock observations and physical-memory headroom in independent paired
processes. Use distinct warmups with one cell per measured cell; the retained
initialization failure here shows that a mismatched warmup set can reject a
campaign before measured traffic. Keep traced prefix-state checks separate from
timing runs, and report their binary/configuration identity when using them as
adjacent correctness evidence.

## Phase 3 continuation — Cgroup pressure boundary

At a 64K configured context with an actual 32K prompt and 3,000 cache slots,
the Q2_0 request completed under a 22-GiB cgroup cap with 7.47 GiB minimum
effective headroom. A matched 18-GiB scope reached the six-GiB guard after the
prompt trace advanced from chunk offset 0 to 512: host `MemAvailable` was still 16.431 GiB,
and the cgroup had no OOM events. For a future Strata + Splash run, sample
whole-device availability and the limiting cgroup's `memory.max -
memory.current` together. Preserve supervisor pressure aborts as incomplete
workloads, separate them from OOM failures, and do not infer a general minimum
from this one pass/abort bracket.
The follow-up 20-GiB run completed the same prompt and matched the 22-GiB
run's final and per-layer GDN fingerprints, while the 22-GiB sample had a
lower minimum effective headroom due to a larger cgroup charge. For Splash,
compare the measured remaining headroom and `memory.events` at each sample;
the configured cap alone does not order outcomes when page-cache charge differs
between starts.
The integration supervisor now writes its minimum host-available and
minimum admission-headroom values separately in each terminal result, while
preserving the raw ancestor samples. Reuse this dual summary in future reports;
older runs require calculating the effective minimum from their `memory.jsonl`.
At the same 5,000-slot/cache setting, a 20-GiB scope completed the exact 32K
prompt and matched the 22-GiB run's final and per-layer GDN fingerprints. This
is a useful same-configuration state control across cgroup caps; it does not
remove the separately observed 3,000-vs-5,000-slot state mismatch. For Splash,
repeat state checks at fixed model, prompt and scheduling configuration before
interpreting capacity changes as harmless from matching output text alone.
At fixed 20-GiB cap, 64K context and 5,000 slots, a 256-token prefill chunk
lowered requested prefill-owner and device peaks by about 80 MiB versus the
512-token control. The minimum cgroup headroom moved in the opposite direction
by 0.73 GiB while host availability increased slightly, reflecting different
page-cache/scope charging in sequential runs. Both produced the same output ID,
but all 36 GDN hashes differed. For Splash, retain chunk size as both a memory
and numerical-state factor; report physical/cgroup telemetry and accepted state
separately, and do not infer which state is better without an oracle.
The same 5,000-slot / prefill-256 request also passed under an 18-GiB scope at
6.49 GiB minimum effective headroom, 0.49 GiB above the unchanged guard, and
matched every persistent hash from its 20-GiB repeat. Keep narrow admitted
passes with their exact model, prompt, cache, chunk, and cgroup context; compare
full hashes as well as output IDs. Do not infer a capacity threshold by
contrasting this with the unmatched 3,000-slot / prefill-512 abort.


## 2026-10-12 — Cache-capacity state carries through long-context continuation

A matched Q2_0 32K-prompt continuation compared 3,000 and 5,000 expert-cache
slots at 64K configured context, using accepted-prefix fingerprints for each of
32 generated tokens. Token IDs matched at each commit, but state fingerprints
differed from the first committed boundary through the end. For future Strata +
Splash work, retain the accepted-prefix state as a separate correctness axis
from generated-text equality, and compare state starting at the first commit
after an exact, hashed prompt. Record which subsystems differ at each boundary;
matching MTP/dead-state fields do not imply matching recurrent/KV state. The
trace was synchronization-heavy and correctness-only. On Apple, identify and
trace the actual Metal/CPU recurrent and attention state owners, keeping
platform-specific memory pressure and allocation evidence separate. This single
Orin prompt/capacity pair does not establish quality impact or explain the
difference; no cache default is promoted and Phase 3 remains open.


## 2026-10-12 — Effective cgroup headroom is an observed runtime condition

For a 32K Q2_0 request, nominal 18-GiB scope was safely aborted at 5.927 GiB
effective headroom, while a separate 19-GiB run completed at 6.98 GiB and
matched its 20-GiB state control. This remains specific to Linux cgroup charging
and page-cache history. In future Strata + Splash work, retain the general
method—record real platform availability, per-process/device allocation and
headroom over time, stop before a documented safety floor, and preserve aborts—
but do not port Linux cap numbers or infer a stable capacity from one run.


## 2026-10-12 — Recover after actual long prompt ingestion

A 32,768-token Q2_0 request followed by a short request passed in one live
Strata process at both 3,000 and 5,000 cache slots. The token IDs matched
across arms, while endpoint fingerprints differed across cache settings. Owner
events left only the model weight arena live after both requests. Carry this pattern to Splash: test request cleanup and a second
request after a real long prompt in one process, trace per-request state owners,
and observe the platform's actual shared-memory availability throughout. Keep
this separate from cancellation recovery and from task-quality evaluation; the
Orin result covers one model/cache/context and says nothing about Metal lifetime
behavior.


## 2026-10-12 — Long-prompt transfer measurement and native artifact counters

The Q2_0 native PLE pack has no `experts.bin`. The 32K transfer harness now
uses an explicit Q2_0 GGUF shard to select the filesystem device for block
telemetry, while `IOAccounting=yes` supplies scoped per-request read deltas.
For future Splash work, select a real model artifact on the measured filesystem
rather than assuming a packed-experts filename; keep scoped I/O and device-wide
block reads labeled separately. This screen compared prefetch page-cache fill
with host staging under an exact long prompt and matched accepted output/state,
but timing and read deltas varied across three pairs. Preserve the paired
uncertainty and do not promote a mode from this point. Also leave context room
beyond prompt plus generation when formatting near-limit test requests.


## 2026-10-12 — Mapped reads versus asynchronous pread at 32K

A separate randomized 32K-prompt screen compared mapped reads with asynchronous
`pread`. All three pairs matched generated IDs, cache capacity and persistent
state, while request time ranged from pread 0.48% faster to 14.58% slower. The
first arm can populate the shared page cache for the second, so lower scoped
read bytes and major faults under pread are not cold-storage evidence. For
Splash, record cache state or use a defensible cache protocol, randomize order,
retain paired state checks, and report uncertainty; do not infer transfer wins
from logical bytes or fault counts alone. See the [full Orin report](../../bench/results/2026-10-12-phase3-q2-actual32k-mapped-pread/README.md).

The same-day Q2_0 admission run at a 19-GiB process cap was repeated with the
same exact prompt, cache and configured context. Both runs passed the six-GiB
supervisor and reproduced prompt-end state; effective headroom minima differed
(6.98 versus 9.11 GiB) as cgroup and page-cache starting conditions changed.
This is a useful pattern for Splash—repeat admission points and compare state
and ownership—but not evidence for a portable cap or a stable capacity curve.
See the [repeat record](../../bench/results/2026-10-12-phase3-q2-actual32k-context64k-19G-repeat2/README.md).

An 8K Q2_0 paired screen compared pageable and pinned host staging buffers.
Three pairs under a 28-GiB cgroup ceiling matched output and persistent state;
each mode requested 337.5 MiB and balanced 256 stage allocations/frees. Timing
was highly variable, so no mode changed. At a 24-GiB ceiling, a separate run
aborted pair 3 at the six-GiB effective-headroom floor while host availability
remained above 17 GiB. For Splash, track pinned host payloads as their own
owner, retain per-request frees, and keep cgroup headroom separate from host
availability. The harness also needs strict context slack beyond prompt plus
output. See the [Orin report](../../bench/results/2026-10-12-phase3-q2-stage-pin-8k/README.md).

Three Q2_0 short-request captures at an 8K configured context each produced
the same four graph-instantiation events and 71,983,104-byte NVMap owner
interval as the separate 32K/spec2 sample. This is a cross-context observation
for one verifier shape; the interval still contains adjacent synchronous
allocations. In Splash, align platform-owner samples to graph lifecycle events
and keep the platform's physical-memory authority separate from owner payloads.
The Orin NVMap count and Linux sampling method do not transfer to Metal.
See the [graph-context report](../../bench/results/2026-10-13-phase3-q2-graph-context8k/README.md).


## 2026-10-13 — Cancel an 8K prefill and recover the service

An exact 8,192-token Q2_0 stream was cancelled after one second, after 512
prompt tokens had been read. The service answered a short follow-up with the
expected `Hello Orin!`; transient requested owners were gone at log end while
the model weight arena remained service-resident. The launch's `--spec 2`
becomes a four-token verifier window because suffix drafting is enabled by
default, while the MTP draft window stays two. For Splash, record user-facing
settings and effective runtime windows separately, and pair cancellation with
a real subsequent request plus owner and platform-memory observations. Keep
that evidence distinct from clean shutdown and from long-context quality. See
the [Orin run](../../bench/results/2026-10-13-phase3-q2-cancel-8k/README.md).

A second exact 8K cancellation/recovery run used a 22-GiB cgroup cap. It passed
with 13.157 GiB minimum effective headroom and the same service-lifetime-only
owner remainder. Pairing the same prompt and binary across scope caps is useful
for Splash admission/recovery testing, but these two runs do not define a
capacity threshold. See the [22-GiB run](../../bench/results/2026-10-13-phase3-q2-cancel-8k-22G/README.md).

An exact 16K request was then cancelled after one second with 512 prompt tokens
read, followed by a successful `Hello Orin!` response from the same service.
At a 28-GiB cgroup ceiling, minimum host availability was 17.10 GiB and
effective scope headroom 14.82 GiB; the requested-owner trace left only the
resident weight arena live. For Splash, sample the effective prompt progress at
disconnect, verify no partial response escaped, then issue a real follow-up on
the same process and reconcile request owners. See the
[Orin 16K run](../../bench/results/2026-10-13-phase3-q2-cancel-16k/README.md).

The same test passed with a 32K actual prompt and 64K context reservation:
512 tokens had been read when the stream closed, and the same service again
returned `Hello Orin!`. Minimum host and cgroup-effective headroom were both
16.38 GiB. For Splash, include at least one near-limit prompt in cancellation
and cleanup tests, but keep admission and quality/recall claims separate. See
the [Orin 32K run](../../bench/results/2026-10-13-phase3-q2-cancel-32k/README.md).


## 2026-10-13 — Align graph-owner counters at millisecond resolution

Sampling the Linux NVMap process-owner table at roughly 2.5-ms actual intervals
showed repeatable 20-ms event-centered changes of 23,117,824 and 22,831,104
bytes around the second and third verifier-graph events in three Q2_0 runs.
No ordinary owner allocation/free event appeared in those windows. The
nearest-sample changes varied from zero to about 2.1 MB as sampling phase
shifted, and the initial verifier/commit events were too close to separate.
For Splash, align the platform's native physical-owner counter to graph
lifecycle event timestamps, retain the sampler cadence/jitter, and report the
bracket width. A repeatable event-aligned delta is useful attribution, but it
still cannot identify graph executable bytes when the platform counter includes
other driver/runtime allocations. NVMap and Linux tracing do not apply to Metal.
See the [Orin trace](../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap/README.md).


## 2026-10-13 — Add a 16K actual-prompt admission point

A Q2_0 service accepted the exact 16,384-token prompt twice under a 19-GiB
cgroup ceiling with a 32K context reservation; both requests generated one
token and passed with 8.686 GiB minimum effective headroom. This fills one
workload-length point between the existing 8K and 32K Orin cases. Instrumented
ownership and state were intentionally not collected, so this does not close
those gates or imply a general capacity. For Splash, preserve actual formatted
prompt length, configured context, output length, physical availability and
cgroup headroom as separate dimensions in the capacity ladder. See the
[Orin admission run](../../bench/results/2026-10-13-phase3-q2-admit16k-19G/README.md).

A traced repeat added accepted-state and owner evidence for that prompt. It
matched the `L=16384` target fingerprint from the same prompt, and all 304
allocations had corresponding frees except the resident model weight arena. A
same-prompt warm-up was rejected by the harness because prompt caching reused
16,377 tokens on the measured call; a distinct exact-length warm-up fixed the
control. For Splash, make cache policy and the warm-up prompt part of the
measurement design, and retain harness failures separately from API/runtime
failures. See the [trace report](../../bench/results/2026-10-13-phase3-q2-admit16k-22G-trace/README.md).

A second 16K admission point passed at an 18-GiB cap. Its minimum effective
headroom (8.338 GiB) was lower than the 19-GiB run (8.686 GiB), despite the
higher nominal cap, because page-cache and cgroup starting conditions varied.
For Splash, measure actual headroom through the run and repeat admission points;
do not infer a monotonic curve from configured caps. See the
[18-GiB run](../../bench/results/2026-10-13-phase3-q2-admit16k-18G/README.md).

The same traced 16K request also passed at an 18-GiB scope cap and reproduced
the target fingerprint, but effective headroom reached only 6.205 GiB, about
0.205 GiB above the guard. For Splash, retain near-floor passes as narrow
observations, preserve an explicit safety margin, and repeat them before
setting any support boundary. See the
[18-GiB traced run](../../bench/results/2026-10-13-phase3-q2-admit16k-18G-trace/README.md).


## 2026-10-13 — Extend pageable/pinned staging screen to a 16K prompt

Three randomized pairs at 16K matched token IDs and persistent state. Pinned
staging had a −2.56% median paired request-time delta, but one large pageable
outlier and only three pairs make it a screening signal. Both modes requested
337.5 MiB and balanced their stage-buffer lifetimes. For Splash, keep the host
stage owner explicit and require an independent confirmation prompt before
concluding that pinning helps end-to-end. See the
[Orin screen](../../bench/results/2026-10-13-phase3-q2-stage-pin-16k/README.md).

The seven-pair held-out confirmation used a distinct 16K formatted prompt and
tracing-off timing arms. It matched output IDs in every pair and found a
−0.23% paired request-time delta (95% interval −2.47% to +0.72%); a separate
traced pair matched state and owner lifetimes. This did not confirm a useful
pinned-stage gain, so preserve pageable staging as the default. For Splash,
keep correctness/ownership runs separate from timing runs when tracing alters
execution, and confirm candidate effects on a distinct prompt. See the
[held-out Orin report](../../bench/results/2026-10-13-phase3-q2-stage-pin-16k-heldout/README.md).


## 2026-10-13 — Confirm mapped reads versus pread on a held-out prompt

A seven-pair Q2_0 16K confirmation found pread 2.23% faster for total request
time, with a paired 95% interval from 1.94% to 3.91% faster. Prompt improved
2.42%, but decode was 6.33% slower; the gain missed the proposed promotion
threshold and no default changed. Pread reduced process major faults by about
99%, while whole-device read counters were lower by 33%; those device counters
include unrelated reads and cache was shared, not flushed. For Splash, keep
host faults, scoped I/O and whole-device reads distinct, and evaluate latency
and faults together: a transfer metric can improve while decode or total
request behavior changes in another direction. Extend the exact-length
held-out prompt helper and store its formatted token IDs for reproducible
cross-engine comparisons. See the
[Orin confirmation](../../bench/results/2026-10-13-phase3-q2-mapped-pread-16k-heldout/README.md).

## 2026-10-13 — Keep prefetch fill separate from host staging

A seven-pair held-out Q2_0 comparison held asynchronous prefetch constant and
changed only whether transferred expert blobs also entered host staging. Every
pair matched output IDs, cache capacity and persistent state. Staging was 0.40%
slower end to end (paired 95% interval 0.17% to 1.86%) and raised median major
faults from 38,262 to 58,975. Shared page-cache conditions and whole-device I/O
counters limit the storage interpretation; board rail readings were not
process-attributed. Keep the fill-only route for this workload and do not infer
a product-wide rule. For Splash, distinguish read scheduling, page-cache fill,
explicit pinned/pageable staging and device ownership as independent factors,
and hold all but one fixed in paired tests. A staging path can alter host faults
without reducing request time. See the [Orin confirmation](../../bench/results/2026-10-13-phase3-q2-prefetch-stage-16k-heldout/README.md).

A separate seven-pair held-out 32K mapped-versus-`pread` comparison passed all
state/output checks but did not resolve the transfer choice: the paired median
request effect was −1.12% for `pread`, while two pair reversals widened the 95%
interval to −1.58% through +16.23%. Major faults fell by about 98% and
whole-device reads by about 32%, yet neither metric established request benefit
under shared page-cache conditions. For Splash, use prompt-length-specific
held-out pairs and report the full paired distribution; reduced host faults do
not guarantee lower request time. See the [Orin confirmation](../../bench/results/2026-10-13-phase3-q2-mapped-pread-32k-heldout/README.md).

At a 65,536-token context, three fresh Q2_0 requests again showed a repeatable
23.1 MB NVMap process-owner bracket around verifier graph event two, but event
three varied from 6.36 to 22.83 MB; the same event at 8,232 context was
22.83 MB in all three runs. Treat event alignment as attribution evidence, not
graph executable sizing. For Splash, repeat platform-native backing traces at
more than one reservation and context, preserve sample jitter, and retain a
non-graph control only if it has equivalent model/service behavior. See the
[Orin 64K trace](../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap-context64k/README.md).

At 64K context with spec4, the second verifier event produced the same
22.90 MB NVMap owner bracket in three fresh requests, close to 23.12 MB for
spec2 at that context. Spec4 instantiated two verifier graphs rather than
spec2's three, while the first-event bracket was only 6.29–8.45 MB. For Splash,
compare like graph lifecycle events at fixed context and preserve event count;
a single process-wide delta cannot be divided by graph count to price each
executable. See the [Orin spec4 trace](../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap-context64k-spec4/README.md).

At 64K context, spec3 passed in three processes and had repeatable second and
third verifier-event brackets (23.78 and 22.83 MB). Native Q2_0 refused spec1
before readiness because the route requires spec >=2. For Splash, record
unsupported window sizes at the route boundary and never compare graph-memory
results across settings that did not execute. See the spec3 trace
(../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap-context64k-spec3/README.md)
and spec1 refusal
(../../bench/results/2026-10-13-phase3-q2-graph-fine-nvmap-context64k-spec1/README.md).

## 2026-10-13 — Preserve quantization contracts in ARM operator comparisons

An exact Q8_0 operator comparison on Orin found ggml's Cortex-A78AE NEON path
about 8× faster than Strata's scalar Q8_0 oracle across three independent
processes, with byte-identical blocks. This is an optimization lead only:
Strata's production worker uses Q8_1 activations, so Q8_0 parity and speed do
not qualify a drop-in replacement. For a future Splash port, first match block
layout, rounding, scale/sum fields and the downstream consumer contract with an
independent oracle; then benchmark the complete CPU/GPU contribution under real
contention. Report operator time separately from model/request results. See the
[Orin experiment](../../bench/results/2026-10-13-phase4-q8-neon-quant/README.md).

A contract-preserving NEON routine is now integrated behind Strata's opt-in
`STRATA_Q8_1_NEON=1` setting. Seven paired process measurements found a 29.7%
operator reduction with a bootstrap interval that excludes zero; exact
scale/code/sum/correction tests include signed half ties. Format labels alone
are insufficient: two blocks both named Q8_1 can still differ in tie behavior.
For Splash, carry the producer's rounding and correction formula through the
consumer boundary, then verify the real CPU/GPU path and held-out requests
before promotion. See the [Orin report](../../bench/results/2026-10-13-phase4-q8_1-neon-contract/README.md).

## 2026-10-13 — Build eager decoding at the routed-expert seam

A genuine no-capture control must preserve the layer's expert contribution.
The Q2_0 path now exposes `session_eager`: call the layer pre/router half,
wait until the mapped host doorbell is visible, dispatch the normal GPU-hit and
CPU-miss callbacks, then run that same layer's post/combine half. This keeps
routing and combine weights aligned while making the synchronization cost
explicit. A direct layer loop with a preinitialized `parts` buffer is not a
valid eager control because it silently omits routed experts.

The eager Q2_0 and captured controls matched all generated token IDs, all nine
final persistent-state fields, and every accepted-prefix trace for MTP-off and
window 2. These are one-run correctness controls; the observed timing is not a
performance result. The exact binary, prompt, memory observations, initial
failed startup probes and reproduction commands are recorded in the
[eager/captured report](../../bench/results/2026-10-13-phase5-q2-eager-captured/README.md).

For future Strata + Splash work, keep this control at the engine's layer
pre/router and post/combine boundary. Map the GPU/CPU expert callback contract,
state advancement, and synchronization semantics to the target backend rather
than copying CUDA doorbell mechanics. If speculation uses a separate verifier,
keep any residency metadata it requires alive even when target decoding is
uncaptured. Compare token output and committed recurrent/KV state at every
shared commit boundary before timing; then randomize paired request runs and
report launch, pool, transfer, and end-to-end costs separately.

## 2026-10-13 — Align adaptive residency with published speculative prefixes

On one Q6_K 2,048-token incident prompt, counting every MTP verifier row and
scheduling swaps by verifier-round count changed adaptive choices and left
accepted state different from MTP-off. An opt-in candidate staged routed-expert
usage per row, committed only rows in the successfully committed output prefix,
counted cadence in published tokens, and shortened a verifier window when it
would cross the next swap boundary. Two paired runs then matched all 32 token
IDs and every shared persistent-state fingerprint between MTP-off and window 4.
The candidate offered/accepted 31/15 drafts on this workload; this is correctness
evidence only, not a performance result or a generally qualified policy. See the
[Orin adaptive investigation](../../bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/README.md).

For a future Strata + Splash port, keep speculative route usage separate from
committed route usage, define the swap cadence against a stable unit such as
published tokens, and make state/residency changes occur at equivalent commit
boundaries across verifier sizes. Check accepted-prefix recurrent and KV state
directly; matching final text does not establish equivalent state. Confirm the
behavior on held-out prompts and formats before measuring or promoting a policy.

## 2026-10-13 — Separate cache/context screening from quality qualification

A three-block randomized Orin screen crossed `--expert-cache` budget arguments
of 3,000/5,000 (largest-expert-blob units) with 8K/16K reservations on the
opt-in IQ1_M Q6 warp-dequant, accepted-only MTP4 route. Every fixed 512/64
request completed without prompt cache reuse and retained the six-GiB host
floor, but reported resident slots under the 5,000 setting ranged from 4,600 to
6,519. Response prose also varied in
some requests, while the 64-token generation cap was too short to meet the
prompt's 200-word rubric. The throughput deltas are therefore screening leads,
not quality-qualified wins. For Splash, record requested and actual allocation
separately, use enough output for a real task-level rubric, and keep screening
cells out of a promotion decision until held-out quality and confirmation pass.
See the [cache/context screen](../../bench/results/2026-10-14-phase6-q6-cache-context/README.md).

A second three-block screen crossed the same Q6 cache-budget arguments with
prefill chunks 32 and 128. Chunk 128 increased measured prompt throughput in
all paired blocks, but actual cache slots still varied under the 5,000 budget
and the fixed 64-token output was too short to check the task rubric. For
Splash, this nominates chunk 128 for a longer task-quality and held-out test;
it is not enough to promote a default. Record throughput, decode, actual slot
allocation and host floor together because a prompt-path win can coexist with a
decode or memory tradeoff. See the [prefill/cache screen](../../bench/results/2026-10-14-phase6-q6-prefill-cache/README.md).

The follow-up used the same exact 512-token task prompt with a 512-token output
allowance across all four cache × prefill conditions. Every answer ended
naturally, met the full 200-word checklist, and ran with no prompt-cache reuse;
minimum host/effective availability was 8.16 GiB and cgroup OOM/limit counters
remained zero. This confirms task completion for one prompt per condition but
does not compare quality or qualify a profile. For Splash, carry the full task
through factor screens and keep per-cell quality evidence separate from
multi-block performance estimates. See the [full-task follow-up](../../bench/results/2026-10-14-phase6-q6-prefill-cache/quality-full-task/README.md).

A seven-pair held-out run compared chunks 32/128 at cache budget 3,000 on a
distinct 1,069-token prompt. Chunk 128 improved median prompt rate by 196.4%
and reduced request time by 65.7%, but its eight generated tokens differed from
the baseline in every pair (each arm was internally stable). For Splash, a
large prefill win still needs an output/state contract check: do not infer
quality from a short, divergent prefix, and keep performance evidence separate
from task completion. Full-length responses on this prompt then ended naturally
and exceeded 200 words at both chunk sizes, but each failed the explicit opening
requirement to start with the processor. Preserve rubric failures per setting;
do not treat a longer answer as a pass. See the [held-out confirmation](../../bench/results/2026-10-14-phase6-q6-prefill-confirm7/README.md)
and [full-task check](../../bench/results/2026-10-14-phase6-q6-prefill-confirm7/quality-full-task/README.md).

A separate 7,498-token IQ1_M prefill-cancellation cell closed the stream after
the first 64-token prompt chunk, logged cancellation before generation, and
served `Hello Orin!` through the same MTP4 service. This confirms that the API
client disconnect reached the engine and recovery completed for that exact
profile; it does not establish post-cancel state-bit parity or cancellation at
other points. For Splash, pair same-service recovery with backend-native cancel
telemetry and direct committed-state checks when the state contract requires
them. See the [cancellation record](../../bench/results/2026-10-14-phase5-q6-prefill-cancel-recovery/README.md).

An eight-delta Q6 MTP4 decode cancellation committed 12 tokens. Three fresh
exact-length references matched the canceled token prefix and all 11 persistent
state fields at four shared commit lengths; the references also matched each
other, and the canceled service recovered. For Splash, compare the canceled
transaction to fresh exact-length references at every shared accepted prefix,
not only at the final output or recovery response. Keep the reference processes
in the same hardware/memory scope, and report prompt cache, artifact and trace
settings with the state result. See the [decode-cancel comparison](../../bench/results/2026-10-14-phase5-q6-decode-cancel-state-parity/README.md).

The same MTP-off/MTP4 state comparison was extended from an 8K to a 16K
retrieval prompt. At 15,003 prompt tokens, both arms returned the three planted
markers and matched all nine state fields at 14 common generated-prefix
boundaries through 41 tokens; MTP4 accepted 30 of 34 drafts. For Splash, scale
the prompt/context without changing the artifact or state-trace contract, and
compare each shared accepted prefix plus task success before considering
performance. Trace and batch settings perturb execution and must stay out of
timing runs. See the [16K trace](../../bench/results/2026-10-14-phase5-q6-mtp-16k-state-parity/README.md).

An elastic-KV grow test reproduced MTP-off/MTP4 state divergence when growth
left 3,793 versus 3,786 resident cache slots, even though token IDs matched. A
follow-up fixed the retained cache floor at 3,793 and let MTP4 allocate fresh
chunks for its extra KV requirement; both arms then matched token IDs and all
nine persistent fields at every shared commit through 32 tokens. For Splash,
log the actual cache slots before and after each KV grow/trim operation, and
separate cache-funded KV from fresh device allocation. A shared startup budget
does not guarantee equal expert residency during growth. See the
[cache-matched elastic-KV result](../../bench/results/2026-10-13-phase5-q6-kvgrow-cachematched/README.md).

Three sequential fresh-service cycles each completed one distinct warmup and
one measured request; after every stop, the loopback port rebound and no engine
PID remained before the next load. For Splash, retain this process/listener
check alongside request success and physical-memory telemetry. It verifies
sequential reload only; it does not establish concurrent serving or a long
reload soak. See the [IQ1_M teardown check](../../bench/results/2026-10-14-phase7-iq1-teardown3/README.md).

A bounded 56×56 image request on the current IQ1_M profile used a separate CUDA
vision process and the local BF16 projector. The API returned HTTP 200 and the
answer identified the checkerboard-like grid and its color gradient; the
supervised run retained 11.99 GiB effective availability. For Splash, record
the encoder, projector and main-model identities separately, count the encoder
in total physical memory, and include fixture-specific visible-content checks.
This is only a small-image smoke, not high-resolution grounding qualification.
See the [vision smoke report](../../bench/results/2026-10-14-phase7-iq1-vision/README.md).

A second request used a 2048×2048 fixture and warmed the CUDA encoder at 1,024
image tokens. The API admitted the request and reported 1,049 total prompt
tokens; the answer hit its 48-token output cap, so it is runtime evidence only.
The 28-GiB supervisor retained 11.76 GiB minimum host availability with zero
cgroup pressure/OOM events. For Splash, separately record requested image-token
count, actual API token usage, response completion status and memory while the
encoder and projector are resident. This does not qualify higher token counts
or visual grounding accuracy; see the same vision smoke report.

A separate 32K near-limit quality run retrieved three facts at early, middle
and late prompt positions and correctly summed their numeric suffixes, then
passed same-service recovery. The exact 30,040-token request took 1,238.9 s and
retained 12.75 GiB minimum effective availability. A first attempt with a stale
expected-token count completed inference but discarded the answer; preserve
such harness failures explicitly and verify final formatted usage before
scoring quality. For Splash, repeat this with independent prompts and tasks
before calling long-context quality supported. See the [Phase 7 report](../../bench/results/2026-10-14-phase7-longquality/README.md).


The cache-matched elastic-KV check also passed on one distinct 15,003-token
prompt at 16K context: MTP-off and MTP4 matched final output/state on
short→long→short-recovery, as well as all three shared long-request commit
states. Both grew to 16,384 cells and trimmed to 2,048 after graph capture.
For Splash, retain this held-out prompt-length extension as one parity cell only;
repeat other cache floors and prompt lengths before generalizing. Preserve the
position-reset trace grouping fix when request logs omit standalone state-hash
delimiters. See the [15K elastic-KV evidence](../../bench/results/2026-10-14-phase5-kvgrow-heldout/README.md).

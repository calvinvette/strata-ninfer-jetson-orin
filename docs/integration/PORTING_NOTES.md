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

Requested settings do not establish executed paths. Strata clamps KV residency
to at least 20,480 tokens: requesting 1024 with a 4096 context remains fully
resident. Save actual engine capabilities before testing and fail unsupported
cells explicitly. Configuration reservation alone does not prove context quality
or near-limit capacity.

Speculation tests must distinguish accepted drafts, the old pending anchor,
licensed outputs, output clipping and retained persistent state. Zero accepted
drafts still consume an anchor; zero published/retained tokens is a different
transaction. Map each engine's boundary before importing replay scenarios.


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

## Make parity readers artifact-aware at the PLE seam

The fixture-free block oracle from Strata upstream PR #568 avoids captures
that were never included in the repository, but its initial reader is tied to
one pack representation: separated 2-bit key codes and FP16 group scales plus
a 32-bit-expanded BF16 value tensor. The downloaded GSQ-RCO Q2_0 artifact keeps
the key in native GGUF Q2_0 blocks and stores the value directly as BF16. The
oracle correctly refuses the different byte spans before comparison. For a
future Strata + Splash integration, derive test input adapters from the source
artifact metadata and pack index, retain exact source-format identities, and
compare both a source-format decode oracle and the backend's actual materialized
weights. Do not fix a failed fixture lookup by substituting a tensor from a
different model cohort; tensor shapes alone do not establish matching values.

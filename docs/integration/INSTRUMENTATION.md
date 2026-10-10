# Owner observations

`STRATA_INTEGRATION_TRACE=1` enables diagnostic records on stderr. It is disabled
when absent or any other value. It changes no admission decision, allocation
size, reservation, scheduling policy, model format or kernel dispatch. The
header is original integration code; no NInfer implementation is copied.

The verifier diagnostic observes `Verifier`. Successful primary arena allocation
records its requested bytes and allocation identity; a successful free records
the same identity. CUDA/HIP records successful window graph instantiations through
`instantiate_evicting`; SYCL's migrated owner records the corresponding single
window graph finalization. Their batch graph coverage is not equivalent yet.
No graph-pool byte value is inferred from graph counts or free-memory deltas.
The primary `SessionState` backing allocation is also observed as one owner
allocation; its carved arrays are not added as separate backing. Layer-stage
and batch-slot session allocations remain outside this trace.
The CUDA/HIP ordinary single-block `ExpertCache` backing has matching
allocation/free events. CUDA segmented-cache mode (`--vram-elastic`) reports
one `expert-cache-vmm-segment` allocation per successfully mapped physical
handle and a matching free after successful unmap/release. The virtual address
range has separate `cuda-vmm-address-range` reserve/release events. This
supports cache shrink/grow observation without treating address reservation as
device memory. Shared KV VMM chunks that move
between cache and KV ownership use a stable physical-chunk owner: allocation
remains live across range transfers and ends only on successful handle release.
`cuda-vmm-range` map/unmap events record those transfers without adding mapped
views to physical-byte totals; the parser checks each mapping against a live
physical handle and range instance. SYCL has a separate cache source and does
not emit these cache events. CUDA/HIP expert-stage buffers report separate
`expert-stage-pinned-host` and `expert-stage-pageable-host` owners with host device
id `-1`; these events distinguish host backing and do not count as GPU memory.
SYCL's migrated expert-source implementation is separate and does not emit these
stage events.

Each record carries schema1, steady-clock seconds, owner label, instance,
allocation identity, device, requested bytes and an event count. The steady
clock aligns with Linux harness monotonic request windows. Instance/address
values identify an observed lifetime and are not durable identifiers across
processes. One stdio call emits a record. Tracing adds host logging work and is
not enabled implicitly by the paired performance harness.

```sh
# Add STRATA_INTEGRATION_TRACE=1 to the explicit engine config's env, then run
# that owned server under run_control.py. Preserve the ordinary config separately.
python tools/integration/owner_observations.py \
  --engine-log build/integration/NEW_RUN/engine.log \
  --output build/integration/NEW_RUN/owner-observations.json
```

The parser rejects duplicate allocation identities, unmatched frees, conflicting
owners and unsupported schema/kinds. VMM segment handles use the same lifetime
checks, so a shrink followed by regrowth can reuse a released handle identity
without overlapping its earlier lifetime. Shared VMM map/unmap records keep a
chunk's allocation lifetime intact while it changes range owners and reject a
release while still mapped. Virtual-address events must match on owner, address,
device and exact size; failed releases stay visible as live ranges at log end.
Address-space bytes, physical handles, mapped ranges and budget reservations
remain separate report dimensions. The physical allocation ledger still tracks
only observed requested payloads. A live allocation at log end is reported
explicitly; process termination may bypass destructors, so this is not
automatically a leak. Absence of records
fails rather than reporting zero usage. Requested bytes exclude allocator backing
granularity, other allocations by the same owner and driver/graph overhead. The
parser is a research observation tool, not another physical-memory authority.
The summary now also reports concurrent allocation-request peaks by device
across all observed owners. It counts each live `(device, allocation identity)`
once; mapped range transfers, repeated/overlapping views, planned reservations
and graph instantiations are excluded. Device-local totals must stay separate:
they do not represent one physical pool on discrete-GPU systems, and untraced
allocations remain outside the totals.

Automatic expert-cache sizing also emits opt-in `reservation` events for its
explicit VRAM slack and any priced MTP bind, owned-prefill workspace and pipeline
workspace. The parser reports these in a separate `planned_reservations` list;
they are cache-sizing inputs, not allocations or measured physical bytes and
must never be added to observed allocations. Manual expert-cache sizing does
not emit them because that path does not subtract these planned holds from an
automatic cache calculation. A reservation's presence does not prove the later
workspace allocation matched its estimate.

The supervised auto-cache trace on 2026-10-09 records 3072 MiB of VRAM slack
and roughly 215 MiB for MTP binding in each paired arm. Although the request
used a 64-token prefill chunk, the sizing predicate expected it to borrow cache
slots and emitted no separate prefill-workspace reservation. Both runtime logs
instead report too few slots to borrow; the prompt path owns buffers with a
measured 228,829,184-byte requested peak. The general 3072 MiB VRAM slack
remained in the cache-sizing budget for later allocations, so this is not an
admission failure or reserve-breach result. It shows a per-component forecast
and owner-path difference; the free-memory margin and overlapping ownership
still need measurement. No pipeline windows were requested.
Thirty instrumented allocations were freed in each arm. The run also retained
an 8-token accepted-prefix failure (`pooled_full` differed); it is reported
separately and is not a memory-pressure abort. A later trace also observed the
235,033,088-byte primary SessionState backing; it remained live at isolated
subprocess termination. See the [Phase 3
reservation observation](../../bench/results/2026-10-09-phase3-reservation-observations/README.md)
and [short-prefix state follow-up](../../bench/results/2026-10-09-short-prefix-state-followup/README.md).

Fresh CUDA evidence records one 77,960,704-byte primary arena allocation and its
release, plus three successful window graph instantiations. Seven real-model
protocol scenarios pass both with tracing enabled and disabled; disabled emits
no integration records. [Evidence](../../bench/results/2026-10-09-verifier-owner-trace/README.md).
This does not establish total verifier ownership, accepted-prefix state parity,
byte-identical long text, or an instrumented performance improvement.

Prefill now records successful owned-vector allocations and frees, including
peer buffers, token buffers and streaming identity tables. Base-backed allocator
slices emit `view` events. Views can overlap, repeat or borrow backing from an
external expert cache; their sizes are never added to observed allocations.
MTP records state/scratch arenas and releases. Its `payload_snapshot` reports the
existing logical weight/head/arena counter separately, never added to arena
bytes or physical memory. Device identities on frees come from the owning device.

The expanded [evidence report](../../bench/results/2026-10-09-prefill-mtp-owner-trace/README.md)
compares owned and borrowed prefill, and trace-off protocol checks. Remaining
sites include verifier mapped staging/auxiliary/batch buffers, MTP weight-load
allocations, layer-stage and batch-slot session arenas, and graph
capture/destroy/pool observations. Phase 3 must distinguish unique physical
backing, views and future reservations. Phase 1 needs explicit counters and unsupported scopes; do not
mistake a partial requested-byte trace for the later accounting gate.

The local Orin [segmented VMM lifecycle check](../../bench/results/2026-10-09-vmm-segment-owner-trace/README.md)
passes the existing shrink/regrow test for uniform and sized expert caches.
Forty-one observed allocation events have matching frees, including the mapped
physical segments. The short test had no model or imposed memory pressure; it
qualifies trace lifecycle and cache data preservation only.
The shared-range [transfer check](../../bench/results/2026-10-09-vmm-segment-owner-trace/README.md)
also records physical chunks once across ownership moves, with 11 matched
map/unmap pairs and no mapping left live at teardown.
The Oct 10 [virtual address reservation follow-up](../../bench/results/2026-10-10-phase3-vmm-va-reservation/README.md)
records address ranges separately from mapped backing in both `vmm_test` and
`expert_cache_segmented_test`; both tests balance reserve/release events and end
with no range live.

Shared owner edits require CUDA/HIP/SYCL builds, including migrated SYCL source
copies where they exist. The latest native build and targeted tests pass for the
expert-stage host lifetime trace and the CUDA segmented-cache owner events.
Fresh one-job maestro1 HIP and SYCL builds include the updated cache header and
pass; the HIP source also includes the VMM trace (compiled out on HIP). The
migrated SYCL expert-source implementation is separate and does not consume the
stage events. maestro1 has no AMD or SYCL device for runtime qualification.
Compilation does not qualify either GPU runtime.

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
owners and unsupported schema/kinds. It tracks only the observed requested
payloads. A live allocation at log end is reported explicitly; process termination
may bypass destructors, so this is not automatically a leak. Absence of records
fails rather than reporting zero usage. Requested bytes exclude allocator backing
granularity, other allocations by the same owner and driver/graph overhead. The
parser is a research observation tool, not another physical-memory authority.

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
allocations, session arenas, expert-cache backing/resizing and graph
capture/destroy/pool observations. Phase 3 must distinguish unique physical backing, views and future
reservations. Phase 1 needs explicit counters and unsupported scopes; do not
mistake a partial requested-byte trace for the later accounting gate.

Shared owner edits require CUDA/HIP/SYCL builds, including migrated SYCL source
copies where they exist. The native CUDA build passes; isolated maestro1 HIP
and SYCL builds are pending for the expanded source. The earlier verifier-only
HIP snapshot compiles; that does not validate the newer prefill/MTP edits. Compilation does not qualify either GPU runtime.

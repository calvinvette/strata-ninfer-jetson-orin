# Q2_0 64K/spec4 graph backing confirmation — Orin — 2026-10-11

Three independent service startups repeated the calibrated NVMap graph-owner
probe at 65,536 configured context, 256 requested expert-cache slots,
`--prefill 512`, and speculation window 4. Each loopback request returned 24
tokens from the same 31-token prompt. The service stayed alive after every
request. All three supervisors passed the six-GiB physical-availability floor;
minimum host `MemAvailable` was 19.87, 19.97, and 19.88 GiB.

Each engine log recorded three successful CUDA graph instantiations, matched
exactly by three integration owner events. For each process, the 20 or 21
NVMap samples in the stable interval before the first graph call were exactly
6,870,433,792 bytes; the 21 samples after the final graph call were exactly
6,919,143,424 bytes. The stable-to-stable process-owner increase was therefore
48,709,632 bytes (46.45 MiB) in all three runs. This is the NVMap owner change
over graph capture/instantiation and adjacent synchronous allocations, not an
isolated executable size or complete physical-memory ledger. It equals the
previously measured interval for the 32K/spec4 configuration; this small set
does not show that graph backing is generally independent of context.

The probe uses the calibrated `LD_PRELOAD` Driver-call timestamp tracer and
root-read NVMap sampler. Those tools were enabled for ownership measurement;
elapsed request times from this run are excluded from timing inference. Clocks
were not controlled and energy was not measured. Raw per-run service config,
API result, engine trace, NVMap samples, and supervisor telemetry are retained
in [repeat 1](../2026-10-11-phase3-q2-graph-context64k-spec4-repeat1/),
[repeat 2](../2026-10-11-phase3-q2-graph-context64k-spec4-repeat2/), and
[repeat 3](../2026-10-11-phase3-q2-graph-context64k-spec4-repeat3/). Model
files remain under `~/models/`.

This qualifies backing attribution for one 64K/spec4 graph sequence. Other
graph shapes, legacy session-token graphs, non-NVMap allocations and true
graph-pool executable costs remain unpriced; Phase 3 remains open.

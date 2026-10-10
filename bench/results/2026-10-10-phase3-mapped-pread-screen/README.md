# Mapped reads versus whole-blob pread — Orin screening — 2026-10-10

This randomized three-pair screen compares the existing mapped-file expert
path (`STRATA_IO_PREFETCH=0`) with whole-blob asynchronous `pread`
(`STRATA_IO_PREFETCH=1`, eight I/O threads). Staging was explicitly disabled
in both arms (`STRATA_IO_PF_STAGE=0`, `STRATA_STAGE_PIN=0`). The candidate
binary, IQ1_M Coder pack and PLE shard were held constant. Every arm used the
same formatted 512-token prompt and generated 64 tokens, with spec4, an 8K
context, requested cache 5,000 (6,519 actual slots), prefill 64, and prompt
cache 6. Pair order was randomized; all six processes ran sequentially under
the ordinary six-GiB supervisor.

All three pairs matched all 64 emitted token IDs and all nine recorded
persistent-state fingerprints. Minimum `MemAvailable` was 8,777,338,880 bytes
(8.17 GiB). Requested CUDA allocation peaks were identical at 13,987,640,784
bytes in each arm. Per-process major faults had medians of 88,267 mapped and
63,477 pread; minor-fault medians were 189,423 mapped and 208,698 pread.
These process counters cover the generation request after engine readiness;
they are not disk-byte counters.

Median engine prompt time was 22,219.8 ms mapped and 21,850.1 ms pread
(pread 1.7% lower). Median decode time was 4,629.0 ms mapped and 5,987.0 ms
pread (mapped 22.7% lower). Paired total prompt-plus-decode deltas for mapped
versus pread were -6.12%, -4.30% and -1.66%. Three pairs are screening
evidence only; no default or general product benefit is claimed. The
instrumented follow-up pair in `counter-diagnostic/` matched output/state too
and did not expose file-tier summary lines through the serve protocol.

The first harness attempt in `supervisor/` stopped after startup because
`/proc/<engine-pid>/io` was absent on this Orin process. The harness now treats
those counters as unavailable and retains process page-fault counts; the
completed rerun is in `retry-supervisor/`. Its `median_process_read_bytes` is
null (unavailable), not zero. No disk read bytes, copy counts or copy latency
were observed. Energy was not measured. Raw tegrastats are retained; CPU clocks
varied, while GPU and EMC clock rates were unavailable. These gaps prevent this
screen from satisfying the full Phase 3 transfer tradeoff gate.

The serving harness and exact raw process fault deltas are retained alongside
the pair results, memory samples and tegrastats. Model artifacts remain in
`~/models/`; no model or build output is stored here.

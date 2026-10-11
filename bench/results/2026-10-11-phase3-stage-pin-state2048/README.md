# Pageable versus pinned staging state and owner check at 2,048 tokens — Orin

Run date: 2026-10-11 on the local `orin1` Orin AGX (ARM64, CUDA 12.6). One
randomized pinned/pageable pair used the same Coder IQ1_M model and MTP
artifacts, a 2,048-token prompt, 64 generated tokens, 3,000 requested cache
slots (3,903 actual), context 8,192, prefill chunk 512 and spec4. Owner and
persistent-state tracing were enabled; timing is excluded because tracing
synchronizes and adds measurement overhead.

Both arms generated identical token IDs and matched all nine persistent-state
fields (`L`, `gdn`, `ple`, `tail`, `dead`, `pooled`, `pooled_full`, `kv`, and
`ple_prev`). Both used 39,649 cache hits of 56,160 lookups. All observed owner
requests balanced at process teardown: pinned had 85 allocations/frees and
pageable had 92. The stage-host owner requested peak payloads of 154,419,200
bytes pinned and 173,056,000 bytes pageable. Those are instrumented requested
bytes, not physical backing or a complete host-memory total. The owner ledger
also excludes graph executable bytes and uninstrumented sites.

The six-GiB supervisor passed with minimum physical `MemAvailable` of
14,282,874,880 bytes (13.30 GiB), with no cgroup memory pressure or OOM events.
This correctness/ownership check complements the separate trace-free seven-pair
timing report at the same prompt length. It does not establish a performance
benefit or promote pinned staging. Raw arm logs and state/owner summaries are in
`experiment/`; supervisor telemetry is in `supervisor/`. Models remain under
`/home/calvin/models/`.

# Q2_0 cancellation and recovery under a 16 GiB cgroup cap — Orin — 2026-10-11

This combines the Q2_0 2,048-token long-prefill disconnect case with an active
cgroup memory cap. The loopback server used the Q2_0 native path, 32,768
configured context, spec4, 256 requested cache slots and prefill 512. A client
closed its streamed response one second after headers, then sent a separate
short request to the same service. The cancellation and recovery both passed;
the recovery returned the expected `Hello Orin!` response.

The engine read 512 of the formatted 2,048 prompt tokens in its first
12,097 ms prefill chunk, generated zero tokens, then recorded cancellation.
It did not stop the active prefill chunk when the client disconnected. The
short request completed in the same process with no prompt-cache reuse.

The process ran in a transient user scope with `MemoryMax=16G`. The scope's
peak `memory.current` was 9,652,891,648 bytes, leaving a minimum effective
cgroup headroom of 7,526,977,536 bytes (7.01 GiB). Host `MemAvailable` stayed
above 20.01 GiB. Thus the admitted request and recovery stayed above the
six-GiB effective floor, but with only about 1.01 GiB of measured margin.

Owner tracing recorded 304 allocations and 303 frees. All request/session,
prefill, verifier and pageable/pinned stage allocations returned to zero;
the 1,485,606,400-byte process-lifetime weight arena remained live until
service exit. These are requested owner bytes, not a physical-memory sum or a
complete graph-pool ledger. GPU clocks were dynamic, EMC sampling was denied,
and energy was not measured. This is one combined pressure/cancellation cell,
not a general capacity claim. The preserved prompt reached only the first 512
tokens before cancellation, so this does not test cancellation at multiple
prefill boundaries or recovery after an allocation failure.

Exact model artifacts remain under `~/models/`; checksums are in
`artifact-identities.json`. The request, engine log, owner accounting and
supervisor telemetry are retained here.

Reproduce:

```sh
systemd-run --user --scope --quiet -p MemoryMax=16G \
  python3 tools/integration/run_control.py \
    --output bench/results/NEW/supervisor --timeout 1200 --sample-clocks -- \
    python3 tools/integration/cancel_long_prefill_recovery.py \
      --config bench/results/NEW/server-config.json \
      --long-workload bench/results/2026-10-09-phase3-fullchunk-2048/workloads.json \
      --output bench/results/NEW/cancellation.json --cancel-after-s 1.0
```

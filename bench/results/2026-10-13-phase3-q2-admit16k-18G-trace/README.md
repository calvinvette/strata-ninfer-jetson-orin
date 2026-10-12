# Q2_0 16K owner/state admission at 18 GiB — Orin — 2026-10-13

This repeated the exact 16K target and distinct 16K warm-up used in the
[22-GiB traced run](../2026-10-13-phase3-q2-admit16k-22G-trace/README.md),
with the same model, candidate binary, context, cache settings and owner/state
instrumentation. Both API calls passed with zero prompt reuse and one output
token. The target emitted `A` and produced the same `L=16384` state fingerprint
as the 22-GiB run:

```
STATE_HASH L=16384 gdn=420275c97dc1984c ple=415abded0af69ad2 tail=7118cbb8d98aafa9 pooled=7cef2f253fe2f66a kv=661ca4b556c787ac mtp=14650fb0739d0383 stale=14650fb0739d0383 dead=31a4bff535844690 pooled_full=cbd76e1953853ca9 ple_prev=248069,271
```

The owner trace recorded 304 allocations and 303 frees. The only requested-live
allocation at log end was the 1,485,606,400-byte service-lifetime weight arena;
host requested-live bytes were zero. The six-GiB supervisor passed with
minimum host availability 18,664,267,776 bytes (17.382 GiB) and minimum
effective cgroup headroom 6,662,733,824 bytes (6.205 GiB). OOM and OOM-kill
counters were zero. The minimum was only about 0.205 GiB above the supervisor
floor, so this is a narrowly passing single cell, not an operating target or
general capacity threshold.

Tracing synchronizes execution; timing and energy are not qualified. Graph
pools, driver-private allocations and uninstrumented physical backing remain
outside the owner ledger. The exact workloads, API result, owner summary,
supervisor telemetry and local engine-log hash are retained. Model artifacts
remain under `~/models/`.

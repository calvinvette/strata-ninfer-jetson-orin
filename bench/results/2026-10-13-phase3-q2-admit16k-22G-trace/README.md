# Q2_0 16K prompt owner and state check — Orin — 2026-10-13

This follow-up used the same exact 16,384-token Q2_0 prompt as the
[19-GiB admission run](../2026-10-13-phase3-q2-admit16k-19G/README.md), with
32,768 configured context, 3,000 requested expert slots, `prompt-cache 6`, and
allocation/state tracing. All runs used the same candidate binary and local
Q2_0 model artifacts under `~/models/strata-orin-validation/`.

The final fresh-prefill run used a separate exact 16,384-token warm-up prompt,
then measured the original target prompt. Both requests passed; the measured
target read all 16,384 tokens with zero cached tokens and generated one token
(`A`). Its end-state fingerprint was:

```
STATE_HASH L=16384 gdn=420275c97dc1984c ple=415abded0af69ad2 tail=7118cbb8f605cd92 pooled=7cef2f253fe2f66a kv=661ca4b556c787ac mtp=14650fb0739d0383 stale=14650fb0739d0383 dead=31a4bff535844690 pooled_full=cbd76e1953853ca9 ple_prev=248069,271
```

The owner trace recorded 304 allocations and 303 frees. At log end, the only
requested-live allocation was the 1,485,606,400-byte service-lifetime weight
arena; host requested-live bytes were zero. This trace does not measure graph
pools, driver-private memory or all physical backing. The supervisor passed
under `MemoryMax=22G`, with minimum host availability 18,680,229,888 bytes
(17.397 GiB) and minimum effective cgroup headroom 10,733,867,008 bytes
(9.997 GiB). OOM and OOM-kill counters stayed at zero. No clock changes or
energy-per-request measurements were made.

Two diagnostic runs are retained. First, the exact prompt was repeated with
`prompt-cache 0`; both requests passed and the owner ledger balanced, but state
hashing is intentionally suppressed when prompt caching is disabled, so that
run has no fingerprints. Next, `prompt-cache 6` was enabled but the harness
warmed up with the same prompt. The second API response was valid and again
returned `A`, but reused 16,377 prompt tokens; the harness correctly marked
that measured sample failed because it required a fresh-prefill control. The
scope stayed above the six-GiB floor (12.56 GiB minimum effective headroom),
with no OOM events. That failed harness qualification is preserved in
`cache6/result.json`; it was not an engine or API failure. The distinct-prompt
warm-up in `fresh/` fixed this measurement design issue.

Timing is not compared across these runs: tracing synchronizes the engine,
clock rates varied, and each condition has one process. The result qualifies
one exact prompt's admission, observed owner cleanup and state fingerprint;
it does not establish task quality, a capacity threshold or a performance
benefit. Raw API results, capabilities, supervisor telemetry, owner summaries
and workload files are retained by subdirectory. Engine logs are ignored by
Git; their hashes are in `SHA256SUMS.txt`.

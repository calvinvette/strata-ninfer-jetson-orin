# Q2_0 32K prompt, 32-token continuation by expert-cache capacity — Orin — 2026-10-12

This correctness diagnostic follows the exact 32,768-token Q2_0 prompt at a configured 65,536-token context with requested expert cache sizes 3,000 and 5,000. It tests whether the cache-capacity state difference already measured at prompt completion propagates into the accepted continuation. It is not a timing or quality test. The model, PLE pack, tokenizer and expert profile are the same local artifacts identified in the [Q2_0 identity record](../2026-10-11-phase3-q2-admission/artifact-identities.json); they remain under `~/models/`. The formatted prompt SHA-256 is `705dea47aafbfc991d0616621f3a13bf0136a43c546d60c7693c2efdced4d3a3`.

Both arms used prefill chunk 512, speculation window 2, workspace reserve 3,072 MiB, prompt cache 6, CPU prefill sharing disabled, and the same greedy sampler. The accepted-prefix trace and GDN state hashing were enabled. Each fresh process ran under `MemoryMax=20G` with the standard six-GiB effective-headroom floor. These are traced correctness runs: synchronous state hashing materially increases decode time, so elapsed/stage times are excluded from performance comparison.

| Requested cache | Result | Generated tokens | Minimum host availability | Minimum effective scope headroom | Elapsed (trace overhead included) | Owner events |
|---:|---|---:|---:|---:|---:|---:|
| 3,000 | pass | 32 | 16.43 GiB | 7.77 GiB | 466.45 s | 304 allocate / 303 free |
| 5,000 | pass | 32 | 13.98 GiB | 7.57 GiB | 465.96 s | 304 allocate / 303 free |

The prompt completed in both runs, both emitted the same 32 token IDs, and all 32 commit records contain the same committed token ID at each boundary. Persistent state differed at the first recorded boundary (`L=32768`) and at every subsequent boundary (`L=32799` final). GDN, tail, pooled, pooled-full, and KV fingerprints differed at all 32 boundaries; PLE differed at 16; stale differed at 3. Dead, MTP, and the PLE previous-token pair matched at every boundary. This localizes the observed difference to persistent state already present by the first accepted commit; it does not establish a quality impact, identify the numerical cause, or imply that final text parity is sufficient.

Each owner summary has 304 allocation and 303 free events, with the 1,485,606,400-byte weight arena live for process lifetime. Owner totals are requested instrumented payloads and do not account for physical graph/driver backing. Both supervisors report pass, no OOM event, and the required six-GiB floor. Host availability and cgroup headroom are separate observations of one physical memory system and are not added.

`comparison.json` contains per-boundary field comparisons and run summaries. Each traced arm retains parsed `accepted-prefix-trace.json`, `owner-summary.json`, workload metadata and supervisor telemetry. Raw engine logs are locally ignored (`*.log`) and remain on the Orin; their SHA-256 values are recorded in `comparison.json`. The earlier untraced 3,000-slot pilot is retained locally for troubleshooting but is not part of the paired result. The parser regression `PYTHONPATH=. python3 tools/integration/test_mtp_cancel_state_parity.py` passed 7/7.

This strengthens the single-prompt cache-capacity state observation across a long continuation, while leaving Phase 3's broad active-pressure/recovery, graph physical-backing, and product-buffer transfer/admission gates open. No cache setting or default is promoted.

# Q2_0 32K prompt GDN state magnitude by expert-cache capacity — Orin — 2026-10-12

This diagnostic compares the persistent float32 GDN state after the same exact 32,768-token Q2_0 prompt at 65,536 configured context, prefill chunk 512, speculation window 2 and a 3,072 MiB workspace reserve. The two fresh processes differed only in requested expert-cache capacity (3,000 versus 5,000 slots); both ran under a transient 20-GiB cgroup cap with the six-GiB effective-headroom supervisor and CPU prefill sharing disabled.

The model revision, prepared pack, and expert-profile identities are retained in the [Q2_0 artifact identity record](../2026-10-11-phase3-q2-admission/artifact-identities.json). Both configs select those same artifacts. The tested executable SHA-256 is `bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.

Both requests passed, consumed all prompt tokens, generated token ID 32, and used the same prompt SHA-256 (`705dea47aafbfc991d0616621f3a13bf0136a43c546d60c7693c2efdced4d3a3`). Cache lookup results were 54/480 at 3,000 slots and 111/480 at 5,000. Minimum effective headroom was 7.02 and 8.33 GiB; minimum host availability was 16.08 and 13.96 GiB. The difference in host and cgroup minima illustrates why these sequential runs are admission observations, not a memory-efficiency ranking.

The final hash fields `gdn`, `tail`, `pooled`, `kv`, and `pooled_full` differ; `ple`, `mtp`, `stale`, `dead`, and `ple_prev` match. Streaming comparison of the 36-layer float32 GDN dumps found:

| Metric | Result |
|---|---:|
| GDN values compared | 29,417,472 |
| Values that differ | 27,746,372 (94.32%) |
| Whole-state relative L2 | 4.687% |
| Whole-state RMS absolute delta | 0.01266 |
| First layer above `1e-6` relative L2 | 3 (relative L2 `1.30e-4`) |
| Largest layer relative L2 | Layer 23: 11.80% |
| Largest element absolute delta | 2.2144 at layer 33 |

Layers 0–2 are equal or differ only near float32 rounding; the state difference becomes material at layer 3 and grows through later layers. This is associated with cache-capacity configurations and their different hit counts. It does not prove that the cache treatment alone caused the difference, identify the responsible kernel, or determine which state is more accurate. Matching output text and token IDs are not state-parity evidence; a task-level quality oracle is still needed. No cache default or quality claim follows.

The two 113-MiB `gdn-state.bin` files are intentionally ignored by Git under the repository's diagnostic-dump rule and remain local in these run directories. Their SHA-256 values, full per-layer comparison, prompt/workload records, engine logs, owner summaries and supervisor telemetry are retained in the report bundle. The comparison utility streams the dumps by layer and rejects malformed shapes or non-finite values.

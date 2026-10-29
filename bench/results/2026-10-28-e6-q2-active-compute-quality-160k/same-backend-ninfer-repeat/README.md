# NInfer same-backend accepted-prefix GDN repeat

The 160K Q2_0 retrieval harness ran strict NInfer twice in separate fresh
engine processes with the same prompt, configuration, and accepted-prefix GDN
capture positions (163840, 163862, 163885). Both runs returned the expected
answer, identical 47 token IDs, and identical residency fingerprint
(`a02fd81e...ddf7`). Final `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`
fingerprints differed, so the repeatability control failed exact persistent-
state parity. `ple`, `dead`, and `ple_prev` matched.

## Layerwise GDN comparison between NInfer runs

The table gives the first layer with combined-state relative L2 >= `1e-6`.
All 36 GDN layers were compared at each position.

| Accepted position | First material layer | Relative L2 |
| ---: | ---: | ---: |
| 163840 (prompt boundary) | 12 | `1.1694e-4` |
| 163862 | 4 | `3.2549e-3` |
| 163885 | 2 | `3.4067e-6` |

Even with the same backend, process restart, workload, token IDs and residency,
the captured GDN trajectories differ. This is direct evidence that the paired
Strata/NInfer cross-backend comparisons are confounded by run-to-run drift; it
does not identify what creates that drift. Do not infer backend causation or
change arithmetic from this control. The next control is an equivalent
Strata/Strata repeat under the identical harness and settings.

The supervised pair took 3,230.7 seconds. Minimum available physical memory
was 7,476,719,616 bytes (6.96 GiB); sampled OOM kills were zero. Clocks were
observed without control, and energy was not measured. The supervisor records
that the command exited nonzero because the exact state-parity gate failed;
the harness itself reports the expected answer/token/residency matches and the
five differing persistent-state fields.

Raw 337 MiB captures, comparator JSON, logs and supervisor samples remain
local-only. The model remains under `~/models/strata-orin-validation/`.

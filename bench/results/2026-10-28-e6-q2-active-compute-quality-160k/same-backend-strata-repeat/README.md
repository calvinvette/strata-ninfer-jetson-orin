# Strata same-backend accepted-prefix GDN repeat

The 160K Q2_0 retrieval harness ran Strata twice in separate fresh engine
processes with the same prompt, configuration, and accepted-prefix GDN capture
positions (163840, 163862, 163885). Both runs returned the expected answer,
identical 47 token IDs, and identical residency fingerprint
(`a02fd81e...ddf7`). Final `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`
fingerprints differed, so exact persistent-state parity failed. `ple`, `dead`,
and `ple_prev` matched.

## Layerwise GDN comparison between Strata runs

The table gives the first layer with combined-state relative L2 >= `1e-6`.
All 36 GDN layers were compared at each position.

| Accepted position | First material layer | Relative L2 | Largest layer relative L2 |
| ---: | ---: | ---: | ---: |
| 163840 (prompt boundary) | none | below threshold; all layers bitwise equal | `0` |
| 163862 | none | below threshold (`1.65e-9` maximum) | `1.65e-9` |
| 163885 | 13 | `5.4927e-4` | `5.2191e-2` |

This one pair shows that Strata also has same-backend GDN drift, though it is
smaller at the first two sampled positions than the NInfer/NInfer control. The
large later-position delta confirms accumulation can emerge later in the
accepted prefix. One pair per backend is not enough to conclude that the
variation profiles differ reliably or to identify their cause. Keep cross-
backend attribution and arithmetic changes on hold.

The supervised pair took 3,250.5 seconds. Minimum available physical memory
was 6,950,387,712 bytes (6.47 GiB); sampled OOM kills were zero. Clocks were
observed without control, and energy was not measured. The supervisor records
a nonzero command exit because the exact state-parity gate failed; answer,
token IDs, and residency checks passed.

Raw 337 MiB captures, comparator JSON, logs and supervisor samples remain
local-only. The model remains under `~/models/strata-orin-validation/`.

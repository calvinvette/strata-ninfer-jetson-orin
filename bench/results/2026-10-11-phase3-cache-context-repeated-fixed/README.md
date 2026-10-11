# Repeated cache-cap × context-reservation screen — Orin — 2026-10-11

This randomized 2×2 Phase 3 screen repeats the earlier cache/context admission
matrix with one warmup and three measured requests in each independently
started server process. All cells used the same 172-token formatted prompt, an
eight-token output cap, the same IQ1_M/MTP artifacts and candidate engine,
prefill 64, spec 4, mmap experts, 3 GiB VRAM reserve, PCIe fraction 0.55 and
prompt-cache disabled. Only requested expert-cache lower bound and max context
changed. The same six-GiB supervisor and loopback API harness wrapped each
cell. Clocks were not fixed, and request repetitions within a server process
are not independent process replicates.

| Cache request | Context | Actual cache slots | Cache requested bytes | Session requested bytes | Minimum `MemAvailable` | Median prompt ms | Median generation ms |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3000 | 4096 | 3903 | 7,985,945,600 | 235,033,088 | 13.21 GiB | 3,670.9 | 468.0 |
| 3000 | 8192 | 3903 | 7,985,945,600 | 343,101,952 | 13.13 GiB | 3,587.9 | 455.1 |
| 5000 | 4096 | 6519 | 13,311,897,600 | 235,033,088 | 8.39 GiB | 3,083.3 | 390.8 |
| 5000 | 8192 | 6519 | 13,311,897,600 | 343,101,952 | 8.34 GiB | 3,022.6 | 395.3 |

All four cells and all 12 measured requests passed; all remained above the
six-GiB physical-memory floor. Raising the requested cache lower bound from
3000 to 5000 increased actual capacity by 2,616 slots and requested device
backing by 5,325,952,000 bytes, while minimum host availability fell by about
4.8 GiB. Raising context from 4096 to 8192 increased the instrumented session
payload by 108,068,864 bytes. The context-related host-availability changes
were smaller than the cache-related changes in these four cells.

The prompt and generation medians are descriptive only. The exact short
workload, three within-process repetitions, dynamic clocks, order, MTP
acceptance variation and absent energy sampling do not establish a stable
performance effect or a generally best cache/context setting. The requested
cache values are lower bounds under the runtime sizing policy. Owner bytes are
requested payloads from instrumented owners, not physical backing or a complete
RAM ledger; `MemAvailable` remains the physical-memory authority. No defaults
changed.

The initial attempt in sibling directory `../2026-10-11-phase3-cache-context-repeated/`
failed before model startup because the shell Python lacked `jinja2`. The fixed
run explicitly used `build/integration/venv/bin/python`; the setup failure is
retained and excluded from the measured matrix. `campaign.json`, per-cell API
responses, exact generated configs, owner summaries, engine logs and supervisor
memory/tegrastats samples are preserved here. Model artifacts remain under
`~/models/`; their hashes are recorded in `artifact-identities.json`.

Reproduce from the repository root:

```sh
build/integration/venv/bin/python tools/integration/cache_context_screen.py \
  --python build/integration/venv/bin/python \
  --config bench/results/2026-10-09-phase3-cache-context-matrix/cache3000-ctx4096/config.json \
  --workloads bench/results/2026-10-09-phase3-cache-context-matrix/workloads.json \
  --output bench/results/2026-10-11-phase3-cache-context-reproduction \
  --cache-values 3000 5000 --context-values 4096 8192 --rounds 3 --seed 20261011
```

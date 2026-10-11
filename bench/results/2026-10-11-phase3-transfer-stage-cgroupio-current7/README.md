# Scoped-I/O confirmation for prefetch staging versus page-cache fill — Orin — 2026-10-11

This randomized seven-pair comparison tests the two opt-in expert-file
prefetch modes at requested cache 5,000 (6,519 actual slots): `prefetch-fill`
reads cold expert blobs with `pread` into the OS page cache, while
`prefetch-stage` places cold blobs in a bounded pageable host buffer for the
GPU cache fill. Both use the exact 512-token/64-output IQ1_M Coder request,
Q2_0 MTP, prefill chunk 64, context 8,192, and CPU prefill sharing disabled.
Prompt SHA-256 is
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`; engine
SHA-256 is
`facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`.
Pair order was randomized with seed `2026101125`.

All 14 arms passed. Every pair matched generated token IDs, all nine
persistent-state fields, and 6,519 admitted cache slots. Minimum physical
`MemAvailable` was 8,758,239,232 bytes (8.16 GiB), above the six-GiB guard.
The staged path served 104–133 prefetched blobs per request, reported 422–471
unused staged blobs, and waited 1.48–1.68 seconds across 1,117–1,199 fetches.
The page-cache-fill path consumed no staged blobs and reported no decode wait.

| Pair | Order | Fill request (ms) | Stage request (ms) | Stage delta | Fill scope reads (GB) | Stage scope reads (GB) | Stage minus fill reads (GB) | Stage host peak (MiB) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | stage / fill | 28,790.5 | 27,827.5 | −3.34% | 8.5877 | 8.5125 | −0.0752 | 109.2 |
| 1 | stage / fill | 28,359.7 | 28,959.2 | +2.11% | 9.0374 | 8.5277 | −0.5097 | 134.6 |
| 2 | stage / fill | 28,435.9 | 28,588.5 | +0.54% | 8.9057 | 8.8397 | −0.0659 | 114.3 |
| 3 | fill / stage | 28,119.5 | 27,971.5 | −0.53% | 8.5081 | 8.3303 | −0.1778 | 109.2 |
| 4 | stage / fill | 28,067.6 | 27,898.7 | −0.60% | 8.3696 | 8.3141 | −0.0555 | 124.4 |
| 5 | fill / stage | 28,473.4 | 28,946.5 | +1.66% | 8.6387 | 9.0136 | +0.3749 | 91.4 |
| 6 | stage / fill | 28,252.4 | 27,999.7 | −0.89% | 8.5641 | 8.5732 | +0.0092 | 116.8 |

Median request time was 28,359.7 ms for fill and 27,999.7 ms for stage. The
paired median stage delta was −0.53%; its 200,000-resample whole-pair bootstrap
95% interval was −0.89% to +1.66%. Median prompt times were 22,451.9 ms fill
and 22,273.8 ms stage; median decode times were 5,980.8 and 6,018.3 ms.
Median scoped reads were 8.588 GB fill and 8.528 GB stage. The paired median
stage-minus-fill read delta was −0.066 GB (95% bootstrap interval −0.178 to
+0.009 GB), which includes zero. Major-fault medians were 63,576 fill and
56,067 stage; minor-fault medians were 202,709 and 219,387.

Owner observations recorded a `expert-stage-pageable-host` requested peak of
95,846,400–141,107,200 bytes (91.4–134.6 MiB) per staged request and zero live
requested bytes at log end. These are requested payload values, not an
independent physical-backing measurement. The cgroup-v2 I/O counter was
calibrated on the same filesystem using a 64 MiB `O_DIRECT` read; the scope
charged exactly 67,108,864 bytes to the NVMe device row.

Read-only clocks remained dynamic: CPU 729–2,202 MHz, GPU 306–1,300.5 MHz,
EMC 3,199 MHz. Tegrastats rail integrals are retained but cover whole-board
activity, not process energy. The timing interval spans zero and the scoped
read interval also includes zero; staging incurs measurable host memory and
decode wait. No transfer mode or default is promoted from this workload/cache
cell.

`experiment/` retains the per-arm engine logs, output and state comparisons,
cgroup reads, fault counts, owner observations and rail samples; `supervisor/`
retains physical-memory/clock samples and tegrastats. The validated cgroup
calibration is documented in the adjacent [page-cache-fill confirmation](../2026-10-11-phase3-transfer-cgroupio-current7/README.md).
Model files and build products remain in their existing local paths.

Reproduce with `tools/integration/run_control.py` and
`tools/integration/file_tier_transfer_parity.py` using `--compare-prefetch-stage`,
`--pairs 7`, `--expert-cache 5000`, and seed `2026101125`. To retain scoped I/O,
run the supervisor inside a temporary `systemd-run --scope
--property=IOAccounting=yes` after dropping to the normal user and device
groups; the exact inner command and supervisor observations are retained in
`supervisor/result.json` and `supervisor/stdout.txt`.

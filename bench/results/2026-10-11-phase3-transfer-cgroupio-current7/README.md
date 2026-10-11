# Scoped I/O confirmation for mapped versus prefetch-fill — Orin — 2026-10-11

This seven-pair same-day run compares the mapped file-tier path with the
existing `STRATA_IO_PREFETCH=1` page-cache-fill mode at requested expert cache
5,000 (6,519 admitted slots). It uses the exact 512-token/64-output IQ1_M
Coder request, Q2_0 MTP, prefill chunk 64, context 8,192, and CPU prefill
sharing disabled. Prompt SHA-256 is
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`; engine
SHA-256 is
`facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`.
Pair order was randomized with seed `2026101105`.

All 14 arms passed. Within every pair, generated token IDs, all nine
persistent-state fields, and actual cache capacity matched. The six-GiB
supervisor measured minimum physical `MemAvailable` of 8,916,979,712 bytes
(8.30 GiB). Median request times were 26,932.4 ms mapped and 28,234.7 ms
prefetch-fill. Median prompt times were 22,288.1 and 22,289.8 ms; median decode
times were 4,692.1 and 6,010.3 ms.

The prefetch-fill arms are labelled `pread` in the existing harness schema.
They set `STRATA_IO_PREFETCH=1`, `STRATA_IO_PF_STAGE=0`: workers use `pread` to
fill the OS page cache, after which the engine reads through its mapped
pointer. In all seven arms, 1,110–1,179 read-ahead blobs were read, but zero
were reported as consumed; decode reported zero waits. This therefore does
not compare mapped reads against a request-path staged-pread source. It records
the effect of page-cache-fill work in this workload/cache profile. The
separately measured `prefetch-stage` mode is the path that can serve a blob
from its staging buffer.

The systemd scope used `IOAccounting=yes`; a separate 64 MiB `O_DIRECT`
calibration on the same model filesystem charged exactly 67,108,864 bytes to
the scope's NVMe device row. The first calibration attempt looked only at the
filesystem partition row and observed zero; cgroup accounting charged the
read to the parent NVMe row. The corrected helper sums positive per-device
scope deltas, reports the device rows, and passes the exact calibration. Both
attempts are retained in `io-calibration*.json`.

| Pair | Order | Mapped request (ms) | Prefetch-fill request (ms) | Mapped delta | Mapped scope reads (GB) | Prefetch-fill scope reads (GB) | Read delta (GB) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | pread / mapped | 26,963.9 | 28,790.3 | −6.34% | 8.258 | 8.818 | −0.560 |
| 1 | mapped / pread | 29,532.1 | 28,128.7 | +4.99% | 7.858 | 8.219 | −0.362 |
| 2 | pread / mapped | 26,753.7 | 28,829.4 | −7.20% | 7.705 | 8.628 | −0.924 |
| 3 | mapped / pread | 26,522.9 | 28,362.3 | −6.49% | 7.830 | 8.570 | −0.739 |
| 4 | mapped / pread | 26,878.8 | 28,234.7 | −4.80% | 8.049 | 8.365 | −0.316 |
| 5 | pread / mapped | 27,087.5 | 28,001.6 | −3.26% | 7.802 | 8.489 | −0.686 |
| 6 | mapped / pread | 26,932.4 | 27,898.8 | −3.46% | 7.976 | 8.644 | −0.668 |

The paired median mapped request delta was −4.80%; a 200,000-resample
bootstrap of whole pairs (seed `2026101105`) gave a 95% interval of −6.49% to
−3.26%. The paired median scoped-read difference was −0.668 GB, with a
bootstrap interval of −0.739 to −0.362 GB. Median scope reads by arm were
7.858 GB mapped and 8.570 GB prefetch-fill. Process major-fault medians were
87,311 and 64,130; minor-fault medians were 181,610 and 202,331. Fault counts
do not establish a uniform fault reduction.

Read-only sampled clocks were dynamic: CPU 729–2,202 MHz, GPU 306–1,300.5 MHz,
and EMC 3,199 MHz. Tegrastats rail integrals are retained but are whole-board
system activity, not process energy. The timing interval and scoped block
reads are observations for the tested page-cache-fill configuration; because
the pread buffers were never consumed, they do not qualify request-path
prefetch performance. No default changed.

`experiment/` retains all arm logs, pair comparisons, state and owner
observations, raw rail samples, read and fault counters. `supervisor/` retains
host memory, clocks and tegrastats; `io-calibration*.json` records the scope
counter check. The Q2_0 PLE/reader CTests and 103 integration Python tests also
passed on this checkout. Model files and build products remain under their
existing local paths.

Reproduce the calibration and experiment from the repository root. Run these
commands inside a temporary `systemd-run --scope --property=IOAccounting=yes`
with the normal user/device groups; the seven-pair run must also be wrapped by
`run_control.py` to retain the six-GiB stop guard. The calibration command is:

```sh
python tools/integration/cgroup_io_calibration.py \
  --path /home/calvin/models/strata-orin-validation/pack/experts.bin \
  --bytes 67108864 --output io-calibration.json
```

The experiment command is the one recorded in `supervisor/result.json` and
`supervisor/stdout.txt`.

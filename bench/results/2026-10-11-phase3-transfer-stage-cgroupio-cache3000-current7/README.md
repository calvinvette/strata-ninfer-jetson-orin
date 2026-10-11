# Scoped-I/O confirmation for prefetch staging at 3,903 cache slots — Orin — 2026-10-11

This randomized seven-pair run compares `prefetch-stage` with `prefetch-fill`
at requested expert cache 3,000 (3,903 actual slots), using the same current
candidate as the 6,519-slot [high-cache confirmation](../2026-10-11-phase3-transfer-stage-cgroupio-current7/README.md).
The exact request has 512 prompt tokens and 64 generated tokens on the IQ1_M
Coder model with Q2_0 MTP, prefill chunk 64, context 8,192, and CPU prefill
sharing disabled. Prompt SHA-256 is
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`; engine
SHA-256 is
`facca01aaf48730f0098fb67b254dd0f42cc063403b03834ed84fa41211dbb83`.
Pair order was randomized with seed `2026101126`.

All 14 arms passed and each pair matched output token IDs, all nine
persistent-state fields, and actual cache capacity. Minimum physical
`MemAvailable` was 13,792,665,600 bytes (12.85 GiB). The staged path served
278–312 prefetched blobs per request, with 550–626 unused blobs and 1.46–1.78
seconds of decode wait. Page-cache fill consumed no staged blobs and reported
no decode wait.

| Pair | Order | Fill request (ms) | Stage request (ms) | Stage delta | Fill scope reads (GB) | Stage scope reads (GB) | Stage minus fill reads (GB) | Stage host peak (MiB) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | stage / fill | 33,372.7 | 32,949.3 | −1.27% | 10.3816 | 10.8585 | +0.477 | 134.6 |
| 1 | fill / stage | 34,505.6 | 33,303.7 | −3.48% | 10.1435 | 10.3112 | +0.168 | 175.3 |
| 2 | stage / fill | 32,959.6 | 32,795.3 | −0.50% | 9.6284 | 10.1717 | +0.543 | 177.7 |
| 3 | stage / fill | 32,946.3 | 32,971.6 | +0.08% | 10.0203 | 10.0378 | +0.018 | 124.4 |
| 4 | fill / stage | 32,973.7 | 33,061.1 | +0.27% | 10.0663 | 10.1115 | +0.045 | 114.3 |
| 5 | fill / stage | 33,382.3 | 32,507.6 | −2.62% | 10.0119 | 9.7081 | −0.304 | 142.2 |
| 6 | fill / stage | 36,882.5 | 33,054.8 | −10.38% | 10.1359 | 10.3899 | +0.254 | 137.2 |

Median request time was 33,372.7 ms for fill and 32,971.6 ms for stage. The
paired median stage delta was −1.27%; its 200,000-resample whole-pair bootstrap
95% interval was −3.48% to +0.08%. One fill arm took 36.88 seconds and is
retained in the analysis. Median prompt times were 26,327.2 ms fill and
26,107.5 ms stage; median decode times were 7,189.5 and 6,781.2 ms.

Median cgroup-scope reads were 10.066 GB fill and 10.172 GB stage. The paired
median stage-minus-fill read delta was +0.168 GB (95% bootstrap interval
+0.018 to +0.477 GB). Major-fault medians were 69,064 fill and 66,498 stage;
minor-fault medians were 269,877 and 287,632. The cgroup v2 `io.stat` counter
was calibrated on the same filesystem with an exact 64 MiB `O_DIRECT` read;
see the adjacent [calibration report](../2026-10-11-phase3-transfer-cgroupio-current7/README.md).

The pageable stage owner reached a requested peak of 119,808,000–186,368,000
bytes (114.3–177.7 MiB) and returned to zero requested bytes at log end. These
are owner-requested payloads, not independently measured physical backing.
Read-ahead and decode waits were captured per arm; board rails are retained as
system-wide measurements and are not process energy. CPU/GPU clocks were
dynamic and EMC was sampled at 3,199 MHz. Although staging was faster in six
of seven pairs, the paired request interval includes zero, staged requests read
more cgroup bytes at the median, and staging allocates host memory and waits
for some blobs. No default changed.

This and the same-binary [6,519-slot confirmation](../2026-10-11-phase3-transfer-stage-cgroupio-current7/README.md)
are cache-stratified results, not a fully randomized cache × staging design:
the two cache strata ran sequentially. They show that staging is actively used
at both capacities, with more blobs served and a larger staging peak at 3,903
slots, but do not establish a general cache interaction or quality result.

`experiment/` retains pair logs, state/owner observations, request counters and
tegrastats rail samples; `supervisor/` retains memory/clock samples and raw
tegrastats. Reproduce with `tools/integration/run_control.py` and
`tools/integration/file_tier_transfer_parity.py`, using `--compare-prefetch-stage`,
`--pairs 7`, `--expert-cache 3000`, seed `2026101126`, and a temporary
`systemd-run --scope --property=IOAccounting=yes` after dropping to the normal
user and device groups. The exact inner command is retained in
`supervisor/result.json` and `supervisor/stdout.txt`.

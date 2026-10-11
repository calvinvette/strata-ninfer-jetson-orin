# Mapped reads versus whole-blob pread — seven-pair confirmation — Orin — 2026-10-10

This randomized, paired follow-up compares the existing mapped expert-file
path (`STRATA_IO_PREFETCH=0`) with whole-blob asynchronous `pread`
(`STRATA_IO_PREFETCH=1`, eight I/O threads). Staging was disabled in both
arms. All 14 supervised requests used the same candidate binary
(`d3e8bcde3a430d7d5bb614fec8ba938398699b9abecd41965bb28fd6d465d721`), IQ1_M
Coder pack and tokenizer, 8K config, fixed requested cache 5,000 (6,519
actual slots), spec4/MTP, prefill 64, the same formatted 512-token prompt
(SHA256 `9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`),
and 64 generated tokens. Pair order was randomized with seed 20261010. Raw
arm logs, result JSON, rail samples, supervisor memory samples and tegrastats
are retained beside this report. Models and packs remain in `~/models/`.

All seven pairs matched the 64 output token IDs and all nine persistent-state
fingerprints. Every request reported 87 drafts and 34 accepted. The fixed
cache kept expert residency constant. The supervisor's minimum physical
`MemAvailable` was 8,601,006,080 bytes (8.01 GiB), above the six-GiB floor.
No allocation refusal or failed request occurred.

| Measure | Mapped median | Pread median |
| --- | ---: | ---: |
| Prompt time | 22,329.2 ms | 22,253.4 ms |
| Decode time | 4,637.3 ms | 6,162.5 ms |
| Prompt + decode | 27,011.2 ms | 28,427.4 ms |
| Process major faults | 90,694 | 65,007 |
| Process minor faults | 190,365 | 211,912 |
| Host NVMe read counter | 8.24 GB | 8.71 GB |

The seven paired mapped-minus-pread request-time deltas were −2.52%, −10.01%,
−5.57%, −4.14%, −4.02%, −4.11% and −4.78%; median −4.14%. A 200,000-draw
bootstrap of the median paired delta (seed 1010, resampling the seven pairs)
gave a percentile interval of −5.57% to −4.02%. Prompt medians were nearly
equal; most of the total-time difference is in decode. This interval describes
this fixed workload and day, not performance across contexts, cache sizes or
hardware conditions.

The median engine-reported `file_mb` was 11,606.2 in both arms. Per-process
`/proc/<pid>/io` read bytes were unavailable. The NVMe counter is whole-device
partition traffic during each request and includes other processes and kernel
readahead; it cannot attribute the observed difference to this process. Major
fault counts were lower with pread, while minor-fault counts were similar.
These counters do not price data copies or establish an isolated device-read
total.

Named tegrastats rail integrals had mapped/pread medians of 193.70/198.88 J
(`VIN_SYS_5V0`), 307.28/317.94 J (`VDD_GPU_SOC`) and 89.73/115.21 J
(`VDD_CPU_CV`). These separate rail estimates include unrelated system work;
they are not process-attributed, additive, or energy-per-request claims. CPU
clocks changed dynamically. GPU and EMC frequency telemetry was unavailable.
The same six-GiB supervisor was active for all requests.

This seven-pair result strengthens the earlier three-pair screen and supports
keeping mapped reads as the measured faster option for this exact workload.
It does not change defaults or establish a broad product win. Process-attributed
disk bytes, isolated copy/transfer latency, GPU/EMC clocks, and repeatability on
other prompt/context shapes remain unmeasured. No transfer path is promoted.

Reproduction command and complete raw values are in `supervisor/result.json`
and `experiment/results.json`. The seven-pair run took 811.8 seconds under
`tools/integration/run_control.py`.

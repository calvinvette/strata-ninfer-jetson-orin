# Calibrated NVMap owner trace of captured-graph startup — Orin — 2026-10-11

The earlier public CUDA Driver interposer saw ten successful graph
instantiations but no public allocation calls. This follow-up measured the
engine process's Linux Tegra NVMap IOVMM client total directly. Before using
that counter for the service, a separate CUDA calibration allocated, touched,
and freed 512 MiB. The `user/strata_cuda_mem` NVMap client increased from
92,119,040 to 628,989,952 bytes while live, an exact 536,870,912-byte delta,
then returned to 92,119,040 bytes after free. The `cuMemGetInfo`, host and
`tegrastats` readings from the earlier calibration did not show that change.
The sanitized owner trace and compact exact-delta summary are in
`nvmap-calibration/`; the raw dump of kernel handle addresses was removed.

The service test used the same candidate engine, IQ1_M artifacts and
seven-scenario API/cancellation-recovery harness as the calibrated graph
probe. A root NVMap client sampler recorded per-PID bytes every 0.1 seconds;
the graph interposer wrote monotonic timestamps for each graph-instantiation
call. Each of three independent process startups passed all seven scenarios
and had ten successful graph instantiations. The interposer still observed
zero public Driver allocations during those calls, while the calibrated
NVMap client counter recorded the following stable-to-stable growth:

| Process | NVMap bytes before graph calls | Bytes after tenth call | Net growth | Minimum host availability |
| --- | ---: | ---: | ---: | ---: |
| Initial | 20,514,680,832 | 20,598,108,160 | 83,427,328 | 7.71 GiB |
| Repeat 1 | 19,176,341,504 | 19,259,768,832 | 83,427,328 | 8.83 GiB |
| Repeat 2 | 20,544,172,032 | 20,627,599,360 | 83,427,328 | 7.69 GiB |

For this IQ1_M service setup, the process-owned NVMap increase across graph
capture and instantiation was exactly 79.5625 MiB in all three processes.
The first baseline was stable for several samples before the first call; the
ending sample followed the tenth call and preceded request-driven allocations.
The capture interval can include other synchronous device-owner allocations,
so this is an interval cost, not an isolated graph-disabled differential or a
universal per-graph executable size. It does replace the previous wholly
unpriced result for this startup path. Broader graph configurations and any
non-NVMap allocations remain outside this measurement.

The sampler reports client name, process, PID, byte total and monotonic/wall
timestamps only; it omits NVMap allocation handles. See `analysis.json` and
`model-artifact-identities.json` for the computed result, exact engine/model
identity and limits. Per-run API logs, timestamped graph events, NVMap samples
and six-GiB supervisor telemetry are retained under this folder. No timing
claim is made.

The NVMap sampler is `tools/integration/nvmap_owner_trace.py`; its parser has
two CPU-only tests. It needs root access to
`/sys/kernel/debug/nvmap/iovmm/clients`. The test-only timestamp interposer is
`graph_driver_probe_timestamp.cpp`, built on Orin with:

```sh
g++ -shared -fPIC -O2 -pthread \
  -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-11-phase3-graph-driver-probe/graph_driver_probe_timestamp.cpp \
  -ldl -o /tmp/strata-graph-driver-probe-timestamp.so
```

Phase 3 remains open for the remaining transfer, admission and broader memory
ownership gates; this one qualified startup does not close the phase.

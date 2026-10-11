# Public Driver API allocation probe around captured graphs — Orin

A test-only `LD_PRELOAD` interposer wrapped the candidate service's runtime
`cudaGraphInstantiate` entry point and public CUDA Driver `cuMemAlloc_v2`,
`cuMemAllocManaged`, and `cuMemFree_v2` calls. It was calibrated in two ways:
the runtime graph calibration emitted a successful instantiate event, and a
direct Driver API calibration emitted a 2 MiB allocation and matching free.
Both calibration commands passed.

The candidate IQ1_M service then passed all seven real-model protocol and
cancellation/recovery scenarios. The interposer observed 10 successful
runtime graph-instantiation calls. It observed no public Driver allocation
events during those calls. Minimum host `MemAvailable` was 10,157,019,136
bytes (9.46 GiB); tracing was used only for accounting, not performance.

The zero Driver allocation count is not evidence that graph executable or
driver storage is zero. The driver allocator wrapper is validated for direct
application calls, but CUDA's runtime/library-internal graph path did not
resolve those allocation calls through the interposed public symbols, or used
other/private APIs. This probe confirms a measurement boundary and does not
alter runtime code or dispatch. The later [calibrated NVMap owner trace](../2026-10-11-phase3-graph-nvmap-calibration/README.md)
measured 83,427,328 bytes of net process-owner growth across ten graph calls in
each of three IQ1_M service startups. That result prices the capture/instantiate
interval for that configuration; the zero public Driver event count above
still cannot be interpreted as zero graph memory.

The run's protocol results and engine log are in `service-run-calibrated/`;
the physical-memory supervisor record is in `service-driver-calibrated/`.
The direct API calibration and result are in `driver_alloc_calibration.cpp`
and `driver-calibration/`. `graph_driver_probe.cpp` is the complete probe
source. Its binary and the calibration executable remain in `/tmp`.

Build and run on Orin with CUDA 12.6:

```sh
g++ -shared -fPIC -O2 -pthread \
  -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-11-phase3-graph-driver-probe/graph_driver_probe.cpp \
  -ldl -o /tmp/strata-graph-driver-probe.so
g++ -O2 -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-11-phase3-graph-driver-probe/driver_alloc_calibration.cpp \
  -L/usr/local/cuda-12.6/targets/aarch64-linux/lib \
  -Wl,-rpath,/usr/local/cuda-12.6/targets/aarch64-linux/lib -lcuda \
  -o /tmp/strata-driver-alloc-calibration
python tools/integration/run_control.py \
  --output bench/results/2026-10-11-phase3-graph-driver-probe/service-driver-calibrated \
  --timeout 1200 -- /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-10-phase3-cancel-recovery/run_cancel_recovery.py \
  --config build/integration/candidate-protocol/server-config.json \
  --output bench/results/2026-10-11-phase3-graph-driver-probe/service-run-calibrated \
  --port 18139 --graph-preload /tmp/strata-graph-driver-probe.so
```

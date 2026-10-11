# Q2_0 public CUDA Driver allocation trace around model graphs — Orin — 2026-10-11

The Q2_0 native verifier request at 32,768 configured context, `--spec 4`,
256 requested cache slots and prefill 512 completed with a 31-token prompt and
24 output tokens. The six-GiB supervisor measured 20.15 GiB minimum host
`MemAvailable`. Three successful runtime graph-instantiation calls matched
three `verifier`/`verifier-commit-graph` integration owner events.

A test-only `LD_PRELOAD` interposer wrapped `cuMemAlloc_v2`,
`cuMemAllocManaged`, `cuMemFree_v2` and the graph instantiate entry points. With
`STRATA_GRAPH_DRIVER_TRACE_ALL=1`, it would report every successful allocation
through those public Driver symbols, even outside graph instantiation. The
model process emitted the three graph-call events and zero allocation-call,
allocation or free events through the wrapped Driver symbols. A separate 2 MiB
direct Driver allocation calibration emitted its allocation call, allocation
and free events with timestamps, validating the trace path.

This narrows the measurement boundary: the observed 48.71 MB NVMap increase is
not explained by calls through these wrapped Driver allocation symbols. The
result does not prove zero graph memory; CUDA runtime/library-private routes,
other allocation APIs and driver-private executable resources remain outside
this interposer. No byte count is assigned to graph executables. The earlier
three-startup NVMap confirmation remains the physical-owner measurement for
this sequence.

Raw Q2_0 request traces, supervisor telemetry, `driver-calibration.txt`,
interposer source, configuration and artifact identities are retained here.
`rerun/` contains the timestamped probe run; the top-level `engine.log`,
`result.json`, `nvmap-clients.jsonl` and `supervisor/` retain the first run
before allocation/free timestamps were added. Both runs had the same three
graph calls and zero intercepted allocation/free events. Model files remain
under `~/models/`.

Reproduce the interposer and calibration on Orin:

```sh
g++ -shared -fPIC -O2 -pthread \
  -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-11-phase3-q2-graph-driver-traceall/graph_driver_probe_timestamped.cpp \
  -ldl -o /tmp/strata-graph-driver-probe-traceall.so
g++ -O2 -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-11-phase3-q2-graph-driver-traceall/driver_alloc_calibration.cpp \
  -L/usr/local/cuda-12.6/targets/aarch64-linux/lib \
  -Wl,-rpath,/usr/local/cuda-12.6/targets/aarch64-linux/lib -lcuda \
  -o /tmp/strata-driver-alloc-calibration
LD_PRELOAD=/tmp/strata-graph-driver-probe-traceall.so \
  STRATA_GRAPH_DRIVER_TRACE_ALL=1 /tmp/strata-driver-alloc-calibration
```

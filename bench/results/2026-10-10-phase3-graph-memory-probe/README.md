# CUDA graph memory API probe — Orin — 2026-10-10

A test-only `LD_PRELOAD` interposer sampled CUDA free bytes and the graph
allocator's used/reserved current and high-water attributes around graph
instantiation, launch and existing synchronization calls. The run used the
candidate IQ1_M service and the seven short real-model protocol scenarios,
including prefill/decode cancellation and recovery. All seven passed; minimum
physical `MemAvailable` was 8,645,984,256 bytes (8.05 GiB). The probe is
diagnostic and was not used for performance timing.

The interposer observed 10 successful `cudaGraphInstantiate` calls and emitted
1,900 snapshots. Every queried graph async-allocator current/high-water value
was zero in this runtime. The before/after `cudaMemGetInfo` endpoint for one
graph-instantiation call showed a largest free-memory drop of 122,507,264 bytes
(116.8 MiB); positive drops across all ten calls summed to 219,836,416 bytes
(209.7 MiB). These are global device-free deltas correlated with calls, not
exclusive graph allocations or transient peaks; other CUDA allocations and
other processes are not separated.

The interposer's scope was checked on Orin with a calibration graph containing
`cudaMallocAsync`/`cudaFreeAsync` nodes requesting 4 MiB. The API read zero
before and after instantiation, then 33,554,432 bytes (32 MiB) used/reserved
after graph launch and synchronization. This validates the sampling path and
also illustrates that the API reports the asynchronous graph allocator. NVIDIA
documents these attributes as memory associated with graph async allocation
nodes, not a complete size for every instantiated executable [CUDA Runtime API
graph management](https://docs.nvidia.com/cuda/archive/12.6.0/cuda-runtime-api/group__CUDART__GRAPH.html).

Strata's captured execution graphs use already allocated buffers and kernel
nodes; they did not use the async graph allocator in this run. Therefore the
zero graph-pool result does not price graph executable/driver objects or close
Phase 3's graph peak-accounting requirement. The per-instantiate free-memory
deltas give a correlated diagnostic only. The full raw log, service run,
supervisor samples, calibration source and interposer source are retained here.
Builds of the interposer and calibration binary were kept outside Git in `/tmp`.

Reproduce on the Orin with CUDA 12.6:

```bash
g++ -shared -fPIC -O2 \
  -I/usr/local/cuda-12.6/targets/aarch64-linux/include \
  bench/results/2026-10-10-phase3-graph-memory-probe/graph_mem_probe.cpp \
  -ldl -o /tmp/strata-graph-mem-probe.so
/usr/local/cuda-12.6/bin/nvcc -O2 -cudart shared \
  bench/results/2026-10-10-phase3-graph-memory-probe/graph_mem_api_calibration.cu \
  -o /tmp/strata-graph-mem-api-calibration
LD_PRELOAD=/tmp/strata-graph-mem-probe.so /tmp/strata-graph-mem-api-calibration
python tools/integration/run_control.py \
  --output bench/results/2026-10-10-phase3-graph-memory-probe/supervisor \
  --timeout 1200 \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-10-phase3-cancel-recovery/run_cancel_recovery.py \
  --config build/integration/candidate-protocol/server-config.json \
  --output bench/results/2026-10-10-phase3-graph-memory-probe/server-run \
  --port 18128 --graph-preload /tmp/strata-graph-mem-probe.so
```

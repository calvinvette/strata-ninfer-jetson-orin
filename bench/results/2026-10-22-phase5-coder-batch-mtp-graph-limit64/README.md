# Default batch-MTP graph limit stress

This supervised current-source run exercised the production default 64-layout
LRU under 80 overlapping requests against the Coder IQ1_M model. The server used
batch size 8 and batch-MTP with the existing Phase 5 graph-lifecycle config.
The driver varied batch layout through staggered request timing; it did not
compare outputs or committed state with serial execution.

The supervisor passed after 811.16 seconds. All 80 requests completed and the
engine captured 90 graph instances spanning 88 unique layouts. The first LRU
eviction followed the 64th unique layout; 26 evictions were logged in total.
Across 784 memory samples, minimum host and admission availability was 11.12
GiB, above the required 6 GiB host headroom. Cgroup low, high, max, OOM and
OOM-kill counters stayed at zero. `analyze_default64.py` checks these lifecycle
and resource conditions; its output is `analysis.json`.

Reproduction from the repository root (model files remain in `~/models/`):

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-22-phase5-coder-batch-mtp-graph-limit64/supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-22-phase5-coder-batch-mtp-graph-limit64/stress_default64.py \
  --config bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json \
  --output bench/results/2026-10-22-phase5-coder-batch-mtp-graph-limit64/run \
  --requests 80
python3 bench/results/2026-10-22-phase5-coder-batch-mtp-graph-limit64/analyze_default64.py
```

The raw engine log and supervisor telemetry are machine-local and omitted from
Git. This result qualifies default-cap eviction/recapture and memory behavior
only. It does not qualify request correctness, serial equivalence, response
quality, throughput, latency or energy. Batch-MTP correctness remains open.

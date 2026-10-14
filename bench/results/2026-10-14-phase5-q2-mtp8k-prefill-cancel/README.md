# Q2_0 8K prefill cancellation and recovery

This Phase 5 check canceled a real Q2_0 request during an exact 8,192-token
prefill, then verified same-service API recovery. It used the current candidate,
16K configured context, 3,000 expert-cache slots, FP16 KV, accepted-only MTP4
at cadence 4, and the Q2_0 assets under `~/models/`. The API stream was closed
15 seconds after response headers arrived. The engine had read 512 prompt
tokens and generated none when it logged cancellation.

The same service then returned the exact recovery response `Hello Orin!` in
7.53 seconds and remained alive. The 28-GiB supervisor passed with minimum
physical host availability and effective admission headroom both 16.712 GiB;
all sampled cgroup pressure and OOM counters were zero. Clocks were observed
without changes; energy is not request-attributed.

This adds one long-prefill cancellation/recovery point for Q2_0 MTP4. It does
not directly compare persistent state after cancellation, test later prefill
positions or mid-chunk cancellation, or establish performance. Raw request,
engine and supervisor records are retained beside this report.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-q2-mtp8k-prefill-cancel/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/cancel_long_prefill_recovery.py \
  --config bench/results/2026-10-14-phase5-q2-mtp8k-prefill-cancel/config-mtp4.json \
  --long-workload bench/results/2026-10-14-phase5-q2-mtp8k-prefill-cancel/workloads.json \
  --output bench/results/2026-10-14-phase5-q2-mtp8k-prefill-cancel/result.json \
  --cancel-after-s 15
```

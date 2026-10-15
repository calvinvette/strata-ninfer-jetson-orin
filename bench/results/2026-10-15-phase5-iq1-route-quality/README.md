# Adaptive-residency recovery task-quality check — Orin — 2026-10-15

This is a held-out exact-answer check for the current-source IQ1_M adaptive
recovery issue. Two fresh service processes each ran the same 512-token
short-task → 2,048-token long request → 512-token short-task sequence. The
short task asked for the exact code `ORCHID-GLACIER-482`; the long request is
the synthetic 2,048-token incident workload used by the current-source route
capture. Generation used temperature zero, MTP off, Q6_K warp-dequant opt-in,
eight workers, FP16 KV, and accepted-only adaptive swaps at cadence four.
CPU/GPU prefill sharing was disabled. Swap byte and residency-table guards
were enabled.

Both services returned the exact code, exactly once, for both short requests.
Within each service, all generated token IDs for the initial and recovery
answers were identical. The six persistent-state fingerprints for GDN, PLE,
tail, pooled state, full pooled state, and KV differed after the long request
in both services. Thus the known state drift reproduced, but this short exact
retrieval task remained correct in both repeats. The long task completed all
16 requested output tokens in each process. This is a narrow quality result
for one code-retrieval task and one sequence; it does not establish general
quality safety or resolve the underlying state discrepancy.

The 28-GiB supervised run took 371.34 seconds. Minimum host availability was
14.07 GiB and minimum effective admission availability was 11.21 GiB. Across
353 one-second samples, cgroup pressure/OOM counters remained zero. The run
used dynamic clocks; EMC readback was denied and request-attributed energy was
not measured.

The exact prompts, token IDs, responses, state fingerprints, logs, clock and
memory samples, and supervisor result are retained under `run/` and
`supervisor/`. `SHA256SUMS.txt` covers the local driver, prompt and config
inputs; `binary-sha256.txt` identifies the executable. The model and prepared
pack remain in `~/models/strata-orin-validation/`; their source shard digests
are recorded in the linked route-capture report. Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G \
  python3 tools/integration/run_control.py \
  --output /tmp/route-quality-supervisor --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-15-phase5-iq1-route-quality/run_route_quality.py \
  --output /tmp/route-quality-run --sessions 2
```

`run_route_quality.py` is the test driver. It builds the exact 512-token short
prompt from the local tokenizer and reuses the retained 2,048-token incident
workload. The executable was SHA256
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`.

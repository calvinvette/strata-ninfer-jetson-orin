# Captured graph memory screen — Orin — 2026-10-10

This screen measured the existing captured service path and attempted an eager
control with the same IQ1_M model, formatted 512-token prompt, 8 generated
tokens, requested 3,000 expert-cache slots, 8,192 context, prefill 64 and MTP
4. It is a memory/correctness diagnostic, not a performance comparison.

The captured arm completed with 3,903 actual cache slots, all eight token IDs
and persistent-state fingerprints recorded, and 13.19 GiB minimum physical
`MemAvailable`. The interposer observed ten successful graph instantiations
and 11,077 snapshots. The largest positive global free-memory drop spanning an
instantiate call was 128,688,128 bytes; positive drops summed to 299,634,688
bytes. Async graph-pool used/reserved attributes remained zero. These global
deltas do not attribute memory exclusively to graph executables or capture
transients. See the earlier [calibrated graph memory API probe](../2026-10-10-phase3-graph-memory-probe/README.md)
for the probe's validation and limitations.

The Orin process-attribution interfaces were also checked: `nvidia-smi --query-compute-apps=pid,used_memory` returns `[N/A]`; `tegrastats --readall` reports system RAM and utilization but no per-process allocation; `/sys/kernel/debug` exposes no NvMap/GPU client tables. Thus there is no independent process-exclusive device-memory counter available here to price graph executable/driver objects.

The paired eager request is unsupported by this service path. The engine's
`--no-capture` implementation enters `session_token`, which has no CPU expert
pool hook; the engine correctly refuses the request unless `--no-pool` is
selected. With `--no-pool`, startup instead fails the profile-filled VRAM
expert-tier admission check before the request. Therefore there is no valid
eager-vs-captured parity or memory result here. Supporting that comparison
requires an eager execution path with the same routed-expert semantics and
admission behavior. Do not interpret captured-arm measurements as a graph
memory estimate or a graph performance win.

The first harness attempt used prompt-cache zero, which suppresses persistent
state fingerprints; it is retained under `attempt-statehash-disabled/` as a
failed setup. `attempt-cpu-pool-guard/` contains the successful captured arm
and the engine refusal of the unsupported eager arm. `rep1/` retains the
separate `--no-pool` startup failure. All runs were under the six-GiB
supervisor; no default or service behavior was changed.

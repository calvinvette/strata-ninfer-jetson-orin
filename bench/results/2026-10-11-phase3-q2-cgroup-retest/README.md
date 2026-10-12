# Current-binary Q2_0 cgroup pressure recheck — Orin — 2026-10-11

This rechecks the earlier active-cgroup admission screen on the current
candidate with a 512-token Q2_0 request, requested 3,000-slot expert cache,
4,096 configured context, one greedy output token, no MTP weights, and the
six-GiB effective-availability floor. Each run used its own transient systemd
scope with the listed `MemoryMax`; the supervisor and engine ran inside that
scope. Raw `memory.jsonl`, cgroup/OOM snapshots, commands, `tegrastats`, and
engine output are retained in each cap directory.

| Scope cap | Actual slots reached | Minimum effective cgroup availability | Minimum host `MemAvailable` | Result |
| ---: | ---: | ---: | ---: | --- |
| 8 GiB | no cache admission | 4.94 GiB | 24.79 GiB | Supervisor pressure abort during startup |
| 10 GiB | 446 | 5.25 GiB | 21.78 GiB | Supervisor pressure abort during prefill allocation |
| 12 GiB | 1,816 | 5.86 GiB | 20.23 GiB | Supervisor pressure abort below the floor |
| 14 GiB | 3,000 | 5.75 GiB | 18.52 GiB | Supervisor pressure abort below the floor |
| 16 GiB | 3,000 | 8.58 GiB | 18.60 GiB | Pass; output token 32 |

No cgroup OOM or OOM-kill event occurred. The supervisor stopped four runs
when cgroup-effective headroom fell below six GiB while host `MemAvailable`
remained much higher. The successful 16-GiB request preserved the required
floor. These results are not a capacity threshold: they are one current-binary
run per cap, without randomized repetitions or paired timing analysis, and
charged cgroup file-cache state varied between runs.

The earlier [Q2_0 cgroup screen](../2026-10-11-phase3-q2-cgroup-admission/README.md)
recorded successful 10/12-GiB cells under its then-current system state. Those
results are retained as historical observations; this recheck shows that the
same caps do not consistently complete when present cgroup pressure differs.
The old 8-GiB run reached a later engine error with no residency table. This
8-GiB recheck was stopped by the supervisor before cache admission, so it does
not reproduce or diagnose that engine error.

No runtime defaults or headroom policy changed. A future admission fix must
reason about the full transition peak (model/session, expert cache and prefill
workspace) before treating the requested cache size as admitted. Broader
repetition and pressure-source isolation remain open Phase 3 work.

# Q2_0 64-token admission repeatability at a 20 GiB cgroup cap — Orin

This follow-up repeats the same Q2_0 cell as the [initial cap sweep](../2026-10-11-phase3-q2-cgroup256-tg64/README.md): 512-token prompt, up to 64 greedy outputs, requested and admitted 256 expert slots, 4K context, native spec2, no MTP, PLE mmap and a 3 GiB workspace reserve. Each fresh process ran in its own 20 GiB cgroup-v2 scope under the six-GiB effective-availability supervisor. Model and pack identities are copied to `artifact-identities.json`; artifacts remain under `~/models/`.

| Run | Result | Output tokens | Minimum effective availability | Minimum host `MemAvailable` | Peak scope `memory.current` |
| --- | --- | ---: | ---: | ---: | ---: |
| Original | Pass | 64 | 7.70 GiB | 21.72 GiB | 12.30 GiB |
| Repeat 0 | Supervisor pressure abort during prefill | 0 | 5.48 GiB | 21.91 GiB | 14.52 GiB |
| Repeat 1 | Pass | 64 | 9.35 GiB | 21.67 GiB | 10.65 GiB |
| Repeat 2 | Pass | 64 | 10.66 GiB | 21.65 GiB | 9.34 GiB |
| Repeat 3 | Supervisor pressure abort during prefill | 0 | 5.55 GiB | 20.90 GiB | 14.45 GiB |

The three completed runs (original plus two passing repeats) emitted the same
64 token IDs. Repeats 0 and 3 were safely aborted during prefill when effective
scope availability crossed the six-GiB guard; host availability stayed above
21.9 GiB and 20.90 GiB, respectively. Repeat 3's cgroup
`memory.events` high/max/OOM/OOM-kill counters stayed zero. Across the four
repeats there are two completed passes and two supervisor aborts. This confirms
a 20 GiB cap is history-sensitive and does not define a safe admission
threshold. A supervisor pressure abort is not an engine OOM or a successful
request; report effective cgroup headroom and outcome with each cell.

The new cgroup `memory.stat` telemetry in Repeat 2 shows why `memory.current`
is not a process-only allocation measure: at its peak sample, 8,291,590,144
bytes were file cache (`file`), including 6,655,135,744 inactive and
1,636,352,000 active; anonymous memory was 1,628,061,696 bytes. The peak sample
reported zero `memory.events` high/max/OOM/OOM-kill events. These counters help
explain cgroup charge composition but do not convert it into GPU-owner bytes.

Raw supervisor logs and telemetry are retained in `rep-00/` through `rep-03/`.
Repeats 0 and 3 were run before the supervisor memory-stat enhancement; Repeat 0
has current/max and host availability only, while Repeat 3 records all cgroup
fields. Repeat 3 ran in a transient systemd scope with `MemoryMax=20G`. Repeat 2
also includes the added `memory.stat` and `memory.events` fields. The
supervisor parser's nine-test suite passes.

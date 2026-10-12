# Q2_0 32K prompt pressure abort at 18 GiB — Orin — 2026-10-12

This pressure probe repeats the 3,000-slot, 32,768-token prompt with a 65,536
configured context from the [22-GiB pass](../2026-10-12-phase3-q2-actual32k-context64k/README.md),
but places the process tree in a transient 18-GiB `MemoryMax` scope. The
existing six-GiB effective-headroom supervisor remained active. Model files
and the Q2_0 pack stayed in `~/models/`; no system service or clock setting
was changed.

The engine loaded the model, admitted the 3,000-slot expert cache and began
the 32K prompt. Its trace advanced from prompt chunk offset 0 to offset 512;
the supervisor terminated the owned process group during subsequent prompt
work when
effective cgroup headroom reached 5.9265 GiB. At that sample, host
`MemAvailable` was still 16.431 GiB, showing why host availability alone did
not describe the scoped limit. The request did not finish and generated no
output token. The final cgroup
sample recorded zero `oom`, `oom_kill` and `oom_group_kill` events. The run is
a pressure abort, not a successful capacity or quality result.

For the same 32K prompt, cache size, context, binary and reserve, the [20-GiB
scope](../2026-10-12-phase3-q2-actual32k-context64k-20G/README.md) completed
with 7.930 GiB minimum effective cgroup headroom; the 22-GiB scope completed
with 7.47 GiB. The 20-GiB process had a lower cgroup charge than the 22-GiB
process, so the outcomes do not form a monotonic capacity curve. Page-cache
charging and initial cgroup state make them configuration-specific
observations, not a general minimum RAM/cgroup setting.

The supervisor retained 38 one-second memory/clock samples, tegrastats, the
engine log and complete cgroup events. The process was stopped by the
supervisor before OOM; owner teardown events are consequently incomplete in
the engine log, while the OS reclaimed the process allocations at exit. No
full request timing or state comparison is reported.

Two earlier launch attempts are retained beside the successful supervisor
invocation. `setup-systemd-run.txt` records an invalid `--wait --scope`
combination rejected before launch. `setup-missing-run-directory/` records a
runner setup error because its output directory had not been created; that
attempt did not load the model or send a prompt. Neither is a model result.

The successful command, exact config and binary identity are in
`supervisor-retry/result.json` and `config-cache3000.json`. It can be repeated
from the repository root with:

```sh
mkdir -p /tmp/q2-actual32k-18g-run
sudo -n systemd-run --scope -p MemoryMax=18G -p MemoryAccounting=yes -- \
  /home/calvin/.local/python/bin/python3 tools/integration/run_control.py \
  --output /tmp/q2-actual32k-18g-supervisor --timeout 1800 --privileged-emc -- \
  /home/calvin/.local/python/bin/python3 \
  bench/results/2026-10-12-phase3-q2-actual32k-context64k/runner.py \
  bench/results/2026-10-12-phase3-q2-actual32k-context64k-18G/config-cache3000.json \
  32768 /home/calvin/workspace/strata-ninfer-jetson-orin/build/integration/candidate/strata \
  /tmp/q2-actual32k-18g-run 65536
```

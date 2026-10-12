# Q2_0 32K prompt pass at 20 GiB — Orin — 2026-10-12

This repeats the 3,000-slot, exact 32,768-token prompt at a 65,536-token
configured context, using the same binary, model files and arguments as the
[22-GiB pass](../2026-10-12-phase3-q2-actual32k-context64k/README.md) and the
[18-GiB pressure abort](../2026-10-12-phase3-q2-actual32k-context64k-18G/README.md).
Only the transient cgroup `MemoryMax` changed. The ordinary six-GiB effective
headroom supervisor remained active.

The 20-GiB run completed all 32,768 prompt tokens and generated token ID 32.
Its exact prompt SHA256 was
`705dea47aafbfc991d0616621f3a13bf0136a43c546d60c7693c2efdced4d3a3`.
Minimum host `MemAvailable` was 16.183 GiB; minimum effective cgroup headroom
was 7.930 GiB. The cgroup recorded no OOM or OOM-kill events. The owner trace
reported 304 allocations and 303 frees, leaving only the expected
1,485,606,400-byte service-lifetime weight arena. The actual expert cache was
3,000 slots; the request recorded 54 hits from 480 lookups and 588.9 MB in its
file-read counter.

The final state fingerprint at `L=32768` and all 36 per-layer GDN fingerprints
were byte-for-byte identical to the earlier 22-GiB run for the same prompt and
configuration. The one emitted token and its state match are consistency
checks for these two runs, not a task-quality or performance result. The
20-GiB single-run prompt time was 169.1 seconds; no timing comparison is
claimed.

The comparison also shows why configured cgroup limits are not a transferable
capacity number by themselves. The 18-GiB scope stopped at 5.927 GiB effective
headroom during early prompt work, while the 20-GiB run completed with 7.930
GiB minimum. The 22-GiB run completed with 7.47 GiB minimum. The charged
memory/page-cache state differed across starts, so the tested outcomes do not
form a monotonic capacity curve. Report `memory.max - memory.current`, host
availability and `memory.events` for every run; retain pressure aborts
separately from OOM failures.

Raw one-second memory and read-only clock samples, tegrastats, the full owner
log, prompt identity and supervisor outcome are retained here. Model files
stayed in `~/models/`; build products and model data are not tracked.

Reproduction from the repository root:

```sh
mkdir -p /tmp/q2-actual32k-20g-run
sudo -n systemd-run --scope -p MemoryMax=20G -p MemoryAccounting=yes -- \
  /home/calvin/.local/python/bin/python3 tools/integration/run_control.py \
  --output /tmp/q2-actual32k-20g-supervisor --timeout 1800 --privileged-emc -- \
  /home/calvin/.local/python/bin/python3 \
  bench/results/2026-10-12-phase3-q2-actual32k-context64k/runner.py \
  bench/results/2026-10-12-phase3-q2-actual32k-context64k-20G/config-cache3000.json \
  32768 /home/calvin/workspace/strata-ninfer-jetson-orin/build/integration/candidate/strata \
  /tmp/q2-actual32k-20g-run 65536
```

# Cgroup-v2 admission guard — 2026-10-10

This check exercised the real Orin cgroup-v2 hierarchy without launching a
model or allocating pressure memory. `run_control.py` was placed inside a
transient systemd user scope with `MemoryMax=1G`; its requested child command
would only print a marker if launched.

The supervisor observed the leaf scope at 6,963,200 bytes current with a
1,073,741,824-byte maximum. Host `MemAvailable` was 26,441,826,304 bytes, but
effective cgroup availability was 1,066,778,624 bytes. Because this is below
the ordinary 6-GiB floor, the result was `pressure_abort` before child launch.
The run wrote no child stdout/stderr files, as expected for a prelaunch abort.
This demonstrates ancestor-aware cgroup admission; it does not test behavior
under an actively pressured cgroup or qualify a lower-floor model run.

The raw result is in `run/result.json`. Reproduce from the repository root:

```bash
systemd-run --user --scope --property=MemoryMax=1G \
  --unit=strata-phase3-cgroup-admission-20261010 \
  python tools/integration/run_control.py \
  --output bench/results/2026-10-10-phase3-cgroup-admission/reproduction \
  -- python -c 'print("SHOULD_NOT_LAUNCH")'
```

# Supervisor headroom-field cgroup calibration — Orin — 2026-10-12

This validates the new `minimum_admission_available_bytes` result field with a
real cgroup ancestor. A trivial child ran under a transient 7-GiB
`MemoryMax=7516192768` scope while `run_control.py` kept its usual six-GiB
floor and sampled host/cgroup memory every second.

The child passed. The terminal result recorded **24.596 GiB** minimum host
`MemAvailable` and **6.991 GiB** minimum effective admission headroom. The
limiting scope was the 7-GiB cgroup; the test did not allocate pressure or
load a model. This confirms that the new summary field follows the actual
limiting ancestor while preserving host availability as a separate quantity.
Raw output, memory samples and cgroup events are in `supervisor/`.

This is a harness calibration only, not model-capacity evidence. The focused
supervisor unit tests and full integration Python suite also pass 12/12 and
118/118.

Reproduce from the repository root with:

```sh
sudo -n systemd-run --scope -p MemoryMax=7G -p MemoryAccounting=yes -- \
  /home/calvin/.local/python/bin/python3 tools/integration/run_control.py \
  --output /tmp/strata-headroom-calibration --timeout 60 --privileged-emc -- \
  /home/calvin/.local/python/bin/python3 -c 'print("headroom field calibration")'
```

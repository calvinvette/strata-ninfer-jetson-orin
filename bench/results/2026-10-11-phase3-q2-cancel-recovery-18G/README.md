# Invalid setup attempt — Q2_0 cancellation cgroup probe — 2026-10-11

This initial invocation did not start the service or model. The harness was
pointed at a nonexistent `bench/results/2026-10-11-phase3-q2-graph-context4k/server-config.json`
path and exited with `FileNotFoundError`. It has no runtime or memory result
and is excluded from the cgroup comparison. The corrected 18 GiB pressure-abort
and 22 GiB pass are retained in their separately reported result directories.

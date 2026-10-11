# Q2_0 graph capture backing by speculation window — Orin — 2026-10-11

This randomized three-pair screen compares first-request graph capture and
instantiation at `--spec 2` and `--spec 4` on the same Q2_0 native model,
4,096 configured context, 256 requested expert-cache slots, 512-token prefill
chunk, and 31-token formatted prompt with 24 generated tokens. The six fresh
service processes ran in order 2/4, 4/2, 2/4. The only configuration difference
was the speculation window. Each process had a 22-GiB cgroup cap and the
standard supervisor six-GiB effective-availability floor.

The request returned the same output text and 31/24 prompt/completion counts in
all six processes. Every supervisor passed with no cgroup OOM events. Minimum
host availability across the six runs was 21.19 GiB; minimum cgroup headroom
was 16.76 GiB. Raw service logs, request results, 10-Hz process NVMap samples,
and supervisor telemetry are retained under each `run-*/` directory.

For each process, the baseline is the median of the last 20 process-owned
NVMap samples before its first graph-instantiation event. The post-capture
value is the median of the last 20 samples after the request completed. The
stable within-process changes repeated exactly:

| Pair | spec2 graph calls | spec2 NVMap change | spec4 graph calls | spec4 NVMap change | spec4 − spec2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 4 | 71,983,104 B | 3 | 48,709,632 B | −23,273,472 B |
| 1 | 4 | 71,983,104 B | 3 | 48,709,632 B | −23,273,472 B |
| 2 | 4 | 71,983,104 B | 3 | 48,709,632 B | −23,273,472 B |

The per-process plateaus were 5,237,268,480 → 5,309,251,584 bytes for spec2
and 5,249,032,192 → 5,297,741,824 bytes for spec4. Because the starting
plateaus differ, the paired comparison uses each process's change, not its
absolute post-request total. The interposer and engine owner records agreed on
the graph-call counts. [`analysis.json`](analysis.json) retains the calculations;
[`analyze.py`](analyze.py) recomputes them from the raw files.

This establishes a repeatable difference between these two exact capture
sequences. NVMap measures process-owned backing over the capture/instantiation
interval; synchronous allocations adjacent to graph creation are included,
and driver-private/non-NVMap allocations remain outside scope. The differing
call counts and graph shapes mean the result is not a per-executable or
per-graph price. It is a memory-configuration observation, not a latency,
quality, or default-selection result. Legacy session-token graphs remain
unsupported on the available native-only pack.

Two setup-only harness failures occurred before an engine started: the first
invoked a misspelled script path, and the second placed the runner above its
per-run configuration. Their supervisor output is retained in
`run-00-spec2/supervisor/` and `supervisor-retry/`. A third invocation hit the
supervisor's existing-output-directory guard before launch. These setup
failures are excluded from the six runtime observations; the successful spec2
run is in `supervisor-retry2/`.

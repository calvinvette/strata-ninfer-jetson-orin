# Q2_0 supervisor clock-observation check — Orin — 2026-10-11

`run_control.py --sample-clocks --privileged-emc` was exercised on the current
CUDA candidate with the Q2_0 native pack, PLE shard, profile, 512-token prompt,
3,000-slot cache request, 4K context, spec2 and one greedy output. The request
passed and emitted token ID 32. Minimum host `MemAvailable` was
19,854,716,928 bytes (18.50 GiB), above the standard six-GiB floor.

The supervisor retained 21 read-only frequency samples in the same timestamped
`memory.jsonl` rows as physical and cgroup memory. GPU rate ranged from 306 MHz
to 1,122 MHz (median 306 MHz); EMC remained at 3,199 MHz. CPU core samples
ranged from 730 MHz to 2,202 MHz (median across core-samples 1,498 MHz). No
clock controls were used. These observations are the brief request window, not
thermal-equilibrium statistics, and the run did not measure process energy.

The harness feature is opt-in. If the clock reader itself raises an exception,
the supervisor records a `sample_error` and continues the workload. The full
integration Python test suite passed 98/98 after this change. Raw command,
clock/memory samples, engine output and tegrastats are retained in `supervisor/`.
The added samples improve clock context in future paired tests; they do not
retroactively repair earlier experiments that did not collect these counters.

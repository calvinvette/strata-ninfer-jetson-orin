# CPU instruction sampling during pp512+tg64 — Orin — 2026-10-10

The candidate API workload completed under the six-GiB supervisor while
Nsight Systems sampled CPU instruction pointers and traced CUDA, NVTX and OS
runtime activity. The minimum sampled `MemAvailable` was 8.07 GiB. Sampling was
enabled with `--sample=process-tree --cpuctxsw=process-tree --backtrace=fp
--samples-per-backtrace=8`; the run command and raw supervisor telemetry are
retained here. The Nsight report and SQLite export are local build artifacts at
`build/integration/nsys-candidate-pp512-tg64/cpu-sampling-profile.{nsys-rep,sqlite}`
and are intentionally not part of Git.

Within the API request window (24.866 seconds, 212,902 sample events across
293 Strata threads), `ExpertPool::worker(int)` accounted for 158,054 sampled
instruction observations (74.2%). Other frequent symbols included
`ggml_vec_dot_iq2_s_q8_K` (7,430), `ggml_vec_dot_iq3_s_q8_K` (7,140),
`ggml_vec_dot_iq3_xxs_q8_K` (7,042), `ggml_vec_dot_iq4_nl_q8_0` (4,162),
`memcpy` (3,920), and `ExpertPool::wait_done` (3,554).

These are sampled instruction counts, not wall-time attribution. In particular,
the worker symbol includes the pool's spin/park loop and cannot be read as 74.2%
CPU utilization or request latency. It motivates a controlled worker-count
screen; it does not identify a kernel or authorize a default change.

The original work used a single same-day process profile, no energy measurement,
and the raw `tegrastats` log. CPU samples are useful even though Nsight Compute
counters and Compute Sanitizer remain unavailable under the current profiling
permissions.

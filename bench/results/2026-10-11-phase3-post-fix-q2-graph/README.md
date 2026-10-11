# Post-fix Q2_0 service and verifier-graph owner check — Orin — 2026-10-11

The rebuilt candidate reran the Q2_0 4K-context, 256-slot, native spec2 service
cell used by the earlier graph-memory follow-up. The real-model protocol suite
passed all seven scenarios: repeated greedy requests, OpenAI and Anthropic
streaming, decode cancellation, and prefill cancellation. Minimum host
`MemAvailable` was 21.15 GiB under the standard six-GiB supervisor. The Q2_0
model and expert pack remain under `~/models/strata-orin-validation/`.

The current binary reports four successful graph-instantiation events: three
`verifier` window graphs and one `verifier-commit-graph`. Its CUDA driver
interposer independently observed four successful calls. The verifier arena
allocation/free balanced 1/1; mapped verifier host allocation/free balanced
16/16; pageable expert staging balanced 256/256; session and expert-cache
owners each balanced 1/1. These are traced owner lifetimes, not total device
memory accounting.

The root-readable Tegra NVMap IOVMM table was sampled every 0.1 seconds. The
stable process-owner sample immediately before the first runtime graph call
was 5,237,268,480 bytes. After the fourth successful call, it was 5,309,693,952
bytes, a 72,425,472-byte increase, identical to the three prior Q2_0 repeats.
This brackets graph capture through first-request instantiation and adjacent
synchronous device allocations; it is not an isolated graph executable size.
After requests completed, the NVMap total later changed as cache pages were
released, so those later samples do not replace the stable graph interval.

The interposer and root-readable NVMap samples are measurement adapters for
this Orin run. The result reconfirms a single Q2_0 graph configuration after
the verifier fix; it does not qualify other graph shapes, cgroup pressure,
energy, or transfer performance. Raw NVMap samples, service/engine logs,
protocol outcomes and supervisor telemetry are retained in this directory.

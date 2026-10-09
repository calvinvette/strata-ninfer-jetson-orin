# Integration status

Initial checkpoint: 2026-10-08. Only the repository, import and plan are delivered.

| Phase | State | Evidence / next gate |
| --- | --- | --- |
| 0 — Repository and import | Complete | Pinned source/evidence manifest, source mapping, plan, offline planner checks |
| 1 — Same-day controls | Not started | Native build and instrumented Coder control; artifact and capability manifest |
| 2 — Operator/state contracts | Not started | Exact target/format mapping and independent oracles |
| 3 — Memory and transfers | Not started | Unique allocation/reservation accounting and pressure/lifetime tests |
| 4 — SM87/ARM kernels | Not started | Profiled bottleneck, qualified candidate, request-level confirmation |
| 5 — Speculation and graphs | Not started | Accepted-prefix state, graph lifetime and drift qualification |
| 6 — Multivariate tuning | Not started | Randomized paired campaign, interactions, uncertainty, held-out confirmation |
| 7 — Capacity and service | Not started | Quality, recovery, thermal equilibrium and sustained workload |
| 8 — Release/upstream | Not started | Relevant backend builds, runtime matrix and reviewable changes |

Inherited results live in [Strata's Orin report](../../bench/results/2026-10-08-jetson-orin/README.md),
[maestro1's backend build report](../../bench/results/2026-10-08-maestro1-builds/README.md),
and [NInfer evidence](../../evidence/ninfer-orin/README.md). These describe their
original revisions and workloads. No integrated-runtime speedup, quality,
capacity, HIP/SYCL execution or desktop byte-identity result is claimed here.

First implementation task: Phase 1 control rebuild and harness adapters. The
offline matrix is a proposal; validate capabilities and resource bounds before
translating it into engine commands. Reuse verified local artifacts by path and
run one model process at a time.

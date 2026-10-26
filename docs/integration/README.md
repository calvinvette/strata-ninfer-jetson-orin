# Strata + NInfer on Jetson Orin

This project starts from Strata's validated ARM64 port and applies the architecture,
correctness methods and measured SM87 lessons from the NInfer Orin port. The first
deliverable was an integration plan and an auditable source/evidence import.

The runtime now has an experimental, opt-in CUDA path for resident Q2_0
Flash-Next experts; Strata continues to own residency, memory, routing and
state. E0–E5 have bounded implementation and test evidence. E6's context
screen is complete, but its performance gate failed, and the E7 assessment
proposes no NInfer release profile. Current-source HIP and SYCL builds and help
checks passed on x86_64 maestro1; accelerator execution remains untested. NInfer
remains opt-in and the default path remains Strata. The latest staged-miss
workload screen has output-hash mismatches in its 557- and 1,069-token cells,
so its performance signal is not quality-qualified. See the [staged screen](../../bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/README.md), [release
assessment](NINFER_E7_RELEASE_ASSESSMENT.md) and [current
status](STATUS.md) for tested limits and open qualification gates.
A 240,286-token held-out retrieval under a 262,144-token cap now passes exact
answer, generated-token and final-state parity for the Q2_0 Strata/NInfer pair;
this is one functional workload, not general long-context quality or
performance qualification.

The earlier phases have bounded closeouts for their tested Strata changes,
correctness gates and profiles. Those closeouts do not establish NInfer expert
execution or a combined-runtime speedup. The [bounded Orin profile](RELEASE_PROFILE.md)
collects the qualified Q2_0 configuration, source/binary identities,
reproduction command, rollback evidence and exclusions.
Current admission, transfer, profiling, speculation and service evidence is
summarized in [status](STATUS.md). See [control reproduction](PHASE1.md) and
[porting notes for future engines](PORTING_NOTES.md) for reproducible methods
and lessons for a future Strata + Splash integration.

Start with the [development plan](PLAN.md), [architecture](ARCHITECTURE.md),
[benchmark protocol](BENCHMARKS.md), [import map](IMPORT_MAP.md), and
[current status](STATUS.md), [Phase 7 evidence matrix](PHASE7_MATRIX.md) and
[Phase 7 closeout](PHASE7_CLOSEOUT.md). Record architectural choices in
[decisions](DECISIONS.md).
The [bootstrap validation](BOOTSTRAP_VALIDATION.md) records the checks performed.

| Project input | Pinned revision | Purpose |
| --- | --- | --- |
| [Strata Orin](https://github.com/calvinvette/strata-inference-orin) | `0be090c8997b24cf5d21557ced40a1b7e93e87d3` | Executable starting point, Flash-Next expert streaming, ARM kernels, physical RAM budgeting, server and validation |
| [NInfer Orin](https://github.com/calvinvette/ninfer-jetson-orin) | `b07248f2528125aeda7550055580204541f1714c` | Reference implementation, operator/state contracts, SM87 schedules, experiments and test methodology |

The [import manifest](../../reference/ninfer-import.json) records every imported
file's source and SHA256. Committed NInfer source is in
[`reference/ninfer`](../../reference/ninfer). Its locally modified plan and ignored
benchmark reports are preserved separately in
[`evidence/ninfer-orin`](../../evidence/ninfer-orin/README.md).

The main development branch is `main`. `origin` is
`https://github.com/calvinvette/strata-ninfer-jetson-orin.git`; `strata-port`,
`ninfer-port` and `upstream` point to the two input ports and Niko1221/Strata.
GitHub returned the existing Strata fork when asked for a second account fork, so
this is an independent GitHub repository preserving Strata's Git ancestry. Existing
upstream PR #1621 remains the Strata portability change.

Quick checks (Python 3.10+, no GPU or model required):

```sh
python3 tools/integration/verify_import.py
python3 tools/integration/plan_matrix.py --output /tmp/strata-ninfer-matrix.json
python3 -m unittest discover -s tools/integration -p 'test_*.py'
git diff --check
```

The matrix command creates experiment specifications only. It does not start a
server, change clocks, stop services, or acquire weights. Phase 1 supplies measured
capabilities and explicit artifact paths before any campaign runs.

Retain Strata's [MIT license](../../LICENSE), the imported NInfer
[Apache-2.0 license](../../reference/ninfer/LICENSE), and the
[attribution record](../../THIRD_PARTY_NOTICES.md). Imported dependencies retain
their own notices.

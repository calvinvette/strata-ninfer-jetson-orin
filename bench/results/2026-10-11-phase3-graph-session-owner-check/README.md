# Session and token graph-owner instrumentation — Phase 3

The integration trace now labels successful graph instantiation at the remaining
Strata graph creation sites as well as the verifier and MTP sites: per-layer
session pre/post/stage graphs, the session token graph, and the generic
`CapturedGraph` registry. CUDA/HIP and SYCL mirrors emit the same owner classes.
Labels are emitted only after successful instantiation. Session/captured-graph
entries use device `-1` because these owner objects do not retain a backend
ordinal; do not interpret that as host memory.

This change makes the paths observable but does not prove runtime coverage for
each configuration. The validated native IQ1_M pack bypasses legacy layer-session
and token graph capture. A post-change Orin run therefore exercised verifier and
MTP only: ten successful runtime instantiations matched ten integration owner
events (3 verifier windows, 1 verifier commit graph, and 6 MTP graphs). All
seven API, streaming, cancellation and recovery scenarios passed under the
six-GiB headroom supervisor; minimum host `MemAvailable` was 8,421,408,768 bytes
(7.84 GiB). The owner ledger balanced 52 allocation/free events with zero
instrumented requested bytes live at log end. The report explicitly leaves the
session graph classes runtime-untested.

The focused five-test Phase 3 CTest selection passed on the new Orin binary,
including the artifact-aware Q2_0 `ple_parity` test; minimum `MemAvailable` was
24.56 GiB. All 75 integration-tooling unittests passed. The native CUDA,
maestro1 HIP and full maestro1 SYCL `strata` targets built successfully. The two
maestro1 builds are x86 compile/link evidence only. The SYCL link used the
installed oneMKL library directory and emitted transitive Intel runtime warnings
for `libOpenCL`; see `backend-builds.json`.

The checked-in [source identities](source-sha256.txt), build identities,
capabilities, raw engine/probe log, protocol report and supervisor telemetry
preserve this cell. No model or build products are included. Phase 3 remains
open for broader graph and memory-pressure coverage, along with transfer cells
that lack supported clock or energy scope.

For future Strata + Splash work, instrument every native graph creation site,
including generic registries, per-layer execution graphs and token/speculation
graphs. Verify successful runtime calls against an independent probe per graph
mode; an unexercised owner label is instrumentation coverage only. Calibrate
Metal/OS memory counters separately and keep graph-call counts distinct from
physical graph-pool bytes.

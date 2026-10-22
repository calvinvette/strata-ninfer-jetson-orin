# Current-source Coder API and cancellation checks — Orin — 2026-10-22

The current CUDA service binary was run through the integration protocol harness
using the pinned Coder IQ1_M configuration, 8K context, MTP4 and adaptive
accepted-only expert updates. All seven scenarios passed: three repeated greedy
requests, OpenAI streaming, Anthropic streaming, decode cancellation, and
prefill cancellation. The two canceled requests were followed by same-process
recovery requests that both returned `Hello Orin!`. Client close followed the
first visible decode delta at 1.64 seconds; the prefill cancellation closed at
0.51 seconds. The harness did not compare persistent-state fingerprints, so
these are API behavior and basic recovery checks, not state-parity evidence.

The supervised retry completed in 34.52 seconds with 12.95 GiB minimum host and
admission availability. Cgroup low/high/max/OOM/OOM-kill counters remained zero.
Clocks were observed dynamically and not controlled; EMC readback was denied;
energy was not attributed. The process used a 28-GiB cgroup limit. One earlier
attempt stopped before API requests because the Python environment lacked the
repository-pinned `requests==2.34.2` dependency. Installing that declared
dependency into the existing Python environment allowed the unchanged harness
to run successfully.

The separately rerun `graph_registry_lifecycle_test` passed on the same current
Orin build. Together with the existing captured-graph trace test, this checks
stable-address replay and caller-driven replacement recapture in the registry
wrapper; it does not exercise the model graph pool's real resize path.

Reproduce the API check from the repository root on Orin with the Coder model
files kept under `~/models/strata-orin-validation/`:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-22-phase5-coder-api-cancellation-current-source/supervisor-retry \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/api_control_block.py \
  --config bench/results/2026-10-19-phase5-coder-current-source-prefill-cancel/server-config.json \
  --workloads bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7/workloads.json \
  --output bench/results/2026-10-22-phase5-coder-api-cancellation-current-source/protocol-result.json \
  --variant baseline --validate-api-only

ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -R '^graph_registry_lifecycle_test$'
```

After these checks, the current ARM64/CUDA tree rebuilt with two jobs and its
full configured CTest suite passed 130/132 tests; the two IQ fixture cases were
skipped because their external fixtures are absent. The external one-layer
Q2_0 S2 pack fixture was supplied to `pool_test`, which passed. This full rerun
is regression coverage, not evidence for the unresolved state or graph-pool
resize contracts.

Phase 5 remains open for adaptive long-chain numerical bounds and direct raw
state/operator localization, end-to-end graph-pool resize/recapture coverage,
and broader cancellation/state contracts.

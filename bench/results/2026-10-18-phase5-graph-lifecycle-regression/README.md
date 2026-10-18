# CUDA graph registry lifecycle regression — Orin — 2026-10-18

This adds a focused CUDA test for the caller-owned lifetime contract around `GraphRegistry`. The initial registry captures a one-token graph over fixed input/output addresses. Three replays update the input buffer in place and verify that the graph reads the new contents at each replay. A duplicate record request for the same key is verified not to execute its body or increase the capture count.

While the first graph is still live, the test allocates replacement buffers and verifies their addresses differ from the still-allocated original buffers. It then destroys the first registry before recording the same graph key against the replacement addresses. Three more replays verify correct output from the replacement storage. This exercises stable-address replay, graph-before-buffer retirement ordering, and caller-driven recapture after a storage replacement. It does not exercise Strata's model graph pool, a real model resize, CUDA allocator internals, or graph-memory pricing.

The candidate tree was based on commit `3c4f1f63c61365c155b94dcf3423b8be32bbea62`; the only product-tree edits for this check are the CUDA/Linux test target in `CMakeLists.txt` and `tests/core/graph_registry_lifecycle_test.cu`. The existing `strata` service binary was unchanged (SHA-256 `dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`). The new test binary SHA-256 is `3870a8e4cdabb41581fc3b8c9607fe111a51703d9af7b85b36bc1228621bd1f7`.

## Validation

On Orin AGX, Release CUDA 12.6, SM87, the target and its engine dependencies built with two jobs. The focused graph tests passed 2/2 (`captured_graph_trace_test` and `graph_registry_lifecycle_test`). The Phase 5 accepted-prefix, verifier, KV, GDN, draft-policy and graph CTest selection passed 21/21 under a 28-GiB scope. The full integration Python unittest suite passed 163/163. Minimum host/effective availability was 24.55 GiB for CTest and 24.56 GiB for Python; sampled cgroup low/high/max/OOM/OOM-kill event counters were zero. No clock controls were used; the run-control logs and raw telemetry are retained here.

Reproduce the focused tests after configuring the CUDA test build with:

```sh
cmake --build build/integration/candidate --target graph_registry_lifecycle_test -j2
ctest --test-dir build/integration/candidate --output-on-failure \
  -R 'graph_registry_lifecycle_test|captured_graph_trace_test'
```

The full selected transaction/graph regression command and integration-suite command are retained in each supervisor's `result.json`. This is lifecycle correctness evidence for the wrapper and caller ordering only. It does not close Phase 5's outstanding state, performance, model-pool resizing, termination, or quality gates, and no runtime default changed.

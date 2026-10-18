# Current CUDA Phase 5 transaction and graph regression — Orin — 2026-10-18

The current candidate CTest tree passed all 20 selected tests covering published-prefix, accepted-usage and accepted-window transactions; QSA/verifier/speculation; KV steps and FP16/INT8/Q4/hybrid formats; GDN recurrence; captured-graph tracing; suffix/draft policies; coupled drafts; and convolution cache. Runtime was 37.1 seconds. The 28-GiB supervisor observed 22.89 GiB minimum host and admission availability, above the six-GiB floor, with zero cgroup low/high/max/OOM/OOM-kill events.

The candidate binary is `build/integration/candidate/strata`, SHA256 `dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`. It was built from source commit `a13685c63c472d08ad7acd929aeb24b09d46e1f8`, which is unchanged by this documentation-only result commit. Tests ran on Orin CUDA; this is not HIP/SYCL or model-quality evidence.

An initial supervised invocation used `/usr/bin/ctest`, whose dynamic executable could not load `libjsoncpp.so.25` in the current environment. It failed before starting tests and is retained under `supervisor/`. The successful retry used the Python CTest wrapper from PATH and passed all 20 tests; its logs and telemetry are under `supervisor-retry/`.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  /home/calvin/.local/python/bin/python3 tools/integration/run_control.py \
  --output bench/results/2026-10-18-phase5-current-cuda-ctest/recheck-supervisor \
  --timeout 900 --interval 1 -- \
  ctest --test-dir build/integration/candidate --output-on-failure \
  -R '^(published_prefix_test|accepted_usage_test|accepted_window_test|qsa_parity|verify_parity|spec_verify_parity|kv_steps_parity|kv_q8_parity|kv_stream_parity|kv_hybrid_parity|kv_q4_parity|verify_batch_parity|captured_graph_trace_test|suffix_drafter_test|draft_policy_test|conv_cache_test|coupled_draft_test|spec_prob_test|gdn_rec_parity|gdn_parity)$'
```

`SHA256SUMS.txt` covers all retained files in this result directory.

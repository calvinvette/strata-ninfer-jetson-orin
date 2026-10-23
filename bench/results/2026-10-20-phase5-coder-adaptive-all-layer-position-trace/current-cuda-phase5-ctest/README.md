# Current CUDA Phase 5 transaction and graph regression — Orin — 2026-10-20

The current integration candidate passed all 20 focused CTests covering
published-prefix, accepted-usage and accepted-window transactions; QSA,
verifier and speculation; KV steps and FP16/INT8/Q4/hybrid formats; GDN
recurrence; captured-graph tracing; suffix/draft policy; and convolution cache.
The test run completed in 37.2 seconds. Candidate `strata` SHA256 was
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`.

The 28-GiB supervisor observed 23.45 GiB minimum host/admission availability,
above the six-GiB floor, over 37 one-second samples. Cgroup low/high/max/OOM/
OOM-kill counters stayed at zero. This is CUDA/Orin unit and contract evidence;
it does not qualify task quality, performance, or HIP/SYCL runtime behavior.

The raw passing CTest and telemetry logs are under `supervisor-retry/`. A first
invocation used an invalid `--ctest` argument and exited before starting tests;
that failed preflight record is retained in `supervisor/`. Reproduce the passing
run with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  /home/calvin/.local/python/bin/python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/current-cuda-phase5-ctest/recheck \
  --timeout 900 --interval 1 -- \
  ctest --test-dir build/integration/candidate --output-on-failure \
  -R '^(published_prefix_test|accepted_usage_test|accepted_window_test|qsa_parity|verify_parity|spec_verify_parity|kv_steps_parity|kv_q8_parity|kv_stream_parity|kv_hybrid_parity|kv_q4_parity|verify_batch_parity|captured_graph_trace_test|suffix_drafter_test|draft_policy_test|conv_cache_test|coupled_draft_test|spec_prob_test|gdn_rec_parity|gdn_parity)$'
```

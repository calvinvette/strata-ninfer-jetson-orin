# Layer-26 GDN prefill and verifier snapshots — Orin — 2026-10-20

This opt-in diagnostic compared two identical 512-token requests in one
adaptive service, with a 2,048-token request between them. It uses the pinned
Coder IQ1_M model recorded in the parent experiment. It is state tracing, not a
performance comparison. Full prefill state hashes were taken after each
64-token chunk; the final FP32 state from each short request and the verifier
pre-state at absolute position 511 were also captured. Raw state dumps remain
outside Git under
`~/models/strata-orin-validation/experiments/phase5-gdn-state/`.

The initial and recovery short requests had identical full-state hashes at
prefill boundaries 64, 128, 192, 256, 320, 384, 448 and 505. Their raw end of
prefill states were bit-identical: all 786,432 recurrent values and 30,720
convolution-history values matched. The full-width hash at boundary 505
cross-checked against the existing per-layer prefill hash on both requests.

At verifier position 511, the initial and recovery pre-verification recurrent
matrices differed in 688,243 of 786,432 values, with maximum absolute
difference 0.000177987 and relative L2 difference 0.00046514. All 30,720
convolution-history values matched. This is consistent with the previously
observed recovery divergence residing in the incoming recurrent matrix. The
matching prefill states show that the difference was introduced after the
captured prefill boundary and before the verifier snapshot; they do not identify
the exact token or state transition. The prefill batch ended at internal
boundary 505, whereas the verifier sample is labeled position 511. Because
these are different execution boundaries, prefill-to-verifier raw-array deltas
are not interpreted as same-time parity evidence.

The supervised run passed at `MemoryMax=28G` in 183.79 s. Minimum host and
admission availability were both 14.33 GiB, peak scope memory was 10.77 GiB,
and cgroup low/high/max/OOM/OOM-kill counters remained zero. Clocks stayed
dynamic; energy was not attributed to the request. The run log, raw service
captures and telemetry are retained in `run/` and `supervisor/`; the parsed
array comparison is `prefill-state-analysis.json`.

Reproduce the analysis with the raw dumps from the same Orin host:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_prefill_gdn_boundary_trace.py \
  --service-log bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prefill-state-comparison/run/service.log \
  --state-dump "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-layer26-verifier-pre-2026-10-20.bin" \
  --prefill-state-dump "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-layer26-prefill-final-2026-10-20.bin" \
  --output /tmp/prefill-state-analysis.json
```

# Current-source Coder IQ1_M streamed MTP decode cancellation and recovery — Orin — 2026-10-20

This Phase 5 runtime check canceled a streamed decode on the current candidate
Coder IQ1_M service, then compared every committed prefix against three fresh
exact-length references and checked same-service recovery. The test used the
pinned model revision `5348543e0147355ac9cbcb031184a3546350988e`, base MTP
runtime revision `de4b8e4d43b917e7706784d8bb445c9af86a3540`, FP16 KV and the
configured MTP4 accepted-only profile. The exact candidate executable and
source hashes are in [`source-identity-sha256.txt`](source-identity-sha256.txt);
model and MTP artifact hashes are in
[`artifact-sha256.txt`](artifact-sha256.txt). Artifacts remained under
`~/models/strata-orin-validation/`.

The client closed the stream after eight non-empty deltas (`1 2 3 4 `). The
engine had committed 12 tokens in four verifier commits, accepting 8 of 8
proposed drafts. All three fresh references emitted the same 12 token IDs and
matched all 11 persistent-state fingerprints at shared accepted-prefix lengths
48, 51, 55 and 59. Each reference answer began with the canceled visible text.
The same service remained alive and returned the exact recovery response
`Hello Orin!`.

The 28-GiB supervised run passed in 157.4 s over 151 samples. Minimum host and
admission availability was 13.26 and 12.00 GiB, above the six-GiB floor. Scope
`low`, `high`, `max`, `oom` and `oom_kill` event counters stayed zero. CPU/GPU
clocks were observed dynamically; EMC readback was denied and energy was not
attributed. Raw stream/reference logs, server configs, accepted-prefix traces
and supervisor telemetry are retained in `run/` and `supervisor/`. The focused
cancellation harness tests pass 9/9; integration Python discovery passes
163/163.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/coder-mtp-decode-cancel/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/mtp_cancel_state_parity.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m/config-8192.json \
  --output /tmp/coder-mtp-decode-cancel/run \
  --cancel-chunks 8 --reference-repeats 3 --max-output-tokens 1024
```

This qualifies one current-source MTP4 decode-cancellation point and recovery
sequence. Other cancellation boundaries and profiles remain open; adaptive
CPU/GPU migration parity remains unresolved. Phase 5 stays open.

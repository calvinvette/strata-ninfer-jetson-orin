# IQ1_M decode cancellation state parity

This supervised test canceled an open-ended generation after eight non-empty
stream deltas, then checked the committed prefix against three fresh exact-
length references. All checks passed. The canceled request generated 12 tokens;
the engine recorded eight accepted MTP drafts and one checkpoint. It committed
the same token IDs in the cancellation run and every reference. At each of four
shared accepted-prefix lengths (48, 51, 55 and 59), all 11 persistent-state
fingerprints matched: GDN, PLE, tail, dead, pooled and pooled-full state, KV,
MTP, stale state, and prior PLE tokens. All three references also matched one
another in output text and state. The canceled stream's visible text was a
prefix of each reference. A same-service follow-up returned `Hello Orin!`.

The run used the IQ1_M Coder artifact with Q6_K warp dequant, accepted-only
adaptive swaps at cadence 4, MTP4, FP16 KV, 8K context and a fixed requested
expert cache of 3,000 slots. The cancellation and each reference ran in fresh
service processes sequentially under one 28-GiB user systemd scope. State
tracing was enabled, so no performance conclusion is drawn. The prompt was the
integer-list continuation fixture used by this harness; this is transaction
correctness evidence, not task-quality coverage.

The supervisor passed with minimum host availability of 13.07 GiB and minimum
effective admission headroom of 12.23 GiB, above the six-GiB floor. The cgroup
record shows no OOM event or kill. Full result JSON, server configs, accepted-
prefix traces, engine logs, and memory/tegrastats samples are retained here.
The model shards are the same local IQ1_M artifacts identified in the
[prefill-cancellation record](../2026-10-14-phase5-q6-prefill-cancel-recovery/README.md).

This extends one Q6 MTP4 decode-cancellation point and its exact-length state
comparison. It does not qualify other formats, cache sizes, prompt families,
cancel positions, allocation failures, quality or performance. Phase 5 remains
open.

Reproduce under the same supervisor settings with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output bench/results/2026-10-14-phase5-q6-decode-cancel-state-parity/supervisor \
    --timeout 1800 -- \
    python3 tools/integration/mtp_cancel_state_parity.py \
      --config bench/results/2026-10-14-phase7-q6-recall/config-8192.json \
      --output bench/results/2026-10-14-phase5-q6-decode-cancel-state-parity/result.json \
      --cancel-chunks 8 --reference-repeats 3 --fixed-expert-cache 3000
```

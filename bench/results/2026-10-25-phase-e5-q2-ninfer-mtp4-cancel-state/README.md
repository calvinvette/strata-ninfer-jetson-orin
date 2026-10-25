# E5 Q2_0 NInfer MTP-4 cancellation state check

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This is a bounded
functional/state check for the strict NInfer Q2_0 route with static expert
ownership and MTP-4. It is not a performance measurement or broad Phase 5
qualification.

The service used the same Q2_0 model, pack, tokenizer and 3,000 profile-ranked
expert slots as the [MTP-2 check](../2026-10-25-phase-e5-q2-ninfer-mtp2-cancel-state/README.md).
It used `--spec 4 --mtp-max-t 4`, MTP batch mode 1, strict
`--expert-backend ninfer`, an 8K context, prefill 128, eight CPU workers and
`STRATA_PREFILL_CPU_SHARE=0`. The converted Q2_0 MTP runtime was
`~/models/strata-orin-validation/mtp/rt`; the exact engine arguments are in
[`evidence/engine-config.json`](evidence/engine-config.json). The Release binary
SHA256 was `527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`.
The source MTP artifact and runtime component hashes are recorded in the MTP-2
report.

## State, cancellation and recovery

The existing accepted-prefix parity test canceled after five visible stream
deltas and compared the canceled service against two fresh exact-length
references. All checks passed:

- Nine tokens were committed at accepted-prefix state lengths 48, 52 and 56;
  six MTP drafts were accepted.
- Both fresh references reproduced the committed token IDs and every recorded
  state fingerprint (GDN, PLE, tail, dead, pooled, KV, MTP, stale and previous
  PLE state) at all three boundaries. The two references matched one another.
  The canceled visible text `1 2 3` was a prefix of both full reference
  completions (`1 2 3 4 5`).
- The canceled server remained live and returned `Hello Orin!` to a recovery
  request.
- The engine emitted verifier and MTP prefill/round graph-instantiation events.
  This is graph lifecycle evidence for this workload, not a count of graph
  replays or a guarantee for other window shapes.

The complete comparisons are in
[`evidence/cancel-state-result.json`](evidence/cancel-state-result.json).

## Memory and limits

The supervised run lasted 67.6 seconds. Minimum physical and admission
availability were both 18,025,078,784 bytes (16.78 GiB), above the 6 GiB floor;
cgroup memory events remained zero. Observed CPU clocks ranged from 729.6 MHz
to 2.202 GHz and GPU clocks from 306 MHz to 1.3005 GHz. EMC clock readback was
denied, and energy was not attributed to the request. The supervisor summary is
in [`evidence/supervisor-result.json`](evidence/supervisor-result.json); raw
engine logs and one-second telemetry remain beside the local run output.

This covers one static Q2_0 profile, MTP-4 at one cancellation boundary and one
recovery. It does not test held-out/long retrieval or scoring prompts, adaptive
residency, mixed-codec models or end-to-end performance. E5 remains in progress;
no defaults changed.

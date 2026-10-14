# Q2_0 MTP4 decode cancellation after fresh-sequence reset — Orin — 2026-10-14

This reruns the held-out 7,498-token Q2_0 decode-cancellation state check on the
current service binary after the MTP fresh-sequence reset fix. The API stream
was closed after four nonempty deltas. The canceled service had committed six
tokens, including two accepted drafts, and recovered on the same service with
`Hello Orin!`. Source commit: `2b6dc076`.

Two fresh services processed the same prompt and generated exactly six tokens.
The canceled state, both references and their token IDs matched at all four
shared committed boundaries (sequence lengths 7,498, 7,500, 7,501 and 7,503).
All 11 persistent state fields matched: GDN, PLE, tail, dead, pooled,
pooled-full, KV, MTP, stale, previous PLE tokens and sequence length. The
canceled visible text was a prefix of the exact-length reference output. All
three checks passed.

The run used the Q2_0 MTP4 8K accepted-only profile, FP16 KV, 3,000 fixed expert
slots and a 28-GiB cgroup ceiling. The prompt SHA256 is
`30ec98f48a6861fe1273147cf17763e730e8eec10c1d2e6022801d4ca0eb7997`; the
service binary SHA256 is
`e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`.
Minimum host availability was 16.766 GiB and minimum admission availability
was 7.181 GiB. Cgroup high, max, OOM and OOM-kill counters remained zero.
Peak observed scope usage was 20.819 GiB across 553 telemetry samples.
Clocks were dynamic; energy was not request-attributed. The long prompt took
156.409 seconds to prefill, and six output tokens took 11.382 seconds in the
canceled stream; this is correctness and recovery evidence, not a speed claim.

The retained `run/result.json` contains the exact state hashes and comparisons;
`supervisor/` contains physical-memory samples, cgroup counters, tegrastats and
the command result. The model artifacts remain under `/home/calvin/models/`.
This qualifies one decode-cancellation position and recovery point for this
profile; other termination positions, windows, KV formats, prompts and graph
lifetime conditions remain open.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-q2-mtp4-decode-cancel-post-reset/supervisor \
  --timeout 2400 --interval 1 -- \
  python3 tools/integration/mtp_cancel_state_parity.py \
  --config bench/results/2026-10-14-phase7-q2-recall/config-8192-mtp4.json \
  --output bench/results/2026-10-14-phase5-q2-mtp4-decode-cancel-post-reset/run \
  --cancel-chunks 4 --reference-repeats 2 --fixed-expert-cache 3000 \
  --max-output-tokens 48 \
  --prompt-file bench/results/2026-10-14-phase5-q2-mtp8k-cancel-state-parity/prompt.txt
```

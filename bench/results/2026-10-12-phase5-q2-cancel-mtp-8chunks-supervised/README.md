# Q2_0 MTP decode cancellation and recovery — Orin — 2026-10-12

This extends the earlier one-delta cancellation check by closing the streaming
response after eight non-empty text deltas, during MTP-enabled decode. The
client had received `1 2 3 4 `; the engine had committed 11 token IDs across
six accepted-prefix records at L=48, 50, 52, 54, 56 and 58, including five
accepted draft tokens. The request trace was compared with three fresh exact-
length references. All three references produced the same token IDs; the two
full state comparisons matched all eleven fields at all six shared boundaries.
The reference runs also matched one another.

The canceled service remained alive and returned exactly `Hello Orin!` to a
subsequent request. The 28-GiB systemd scope completed in 123.32 seconds. Its
minimum host availability was 15.09 GiB and minimum effective cgroup admission
headroom was 13.21 GiB, above the six-GiB floor. No OOM events or kills were
recorded. Clocks were observed under the dynamic platform policy, not changed;
EMC readback was denied and energy was not measured.

All runs used the explicit Q2_0 MTP runtime pack, 3,000 expert-cache slots,
CPU-prefill sharing disabled, and accepted-prefix/state tracing. See
`run/result.json` for the direct comparisons and `run/engine-*.log` for raw
state/owner traces. The candidate executable SHA256 is
`1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`.

This is one cancellation point and one prompt. It adds state evidence for an
MTP-active decode cancellation, but does not establish long-prefill
cancellation, broad termination behavior, task quality, or performance. The
preliminary partial attempt in the sibling
`2026-10-12-phase5-q2-cancel-mtp-8chunks/` was started without the standard
cgroup wrapper by mistake, then stopped before its reference matrix completed.
It is retained as diagnostic history and excluded from the result above.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-12-phase5-q2-cancel-mtp-8chunks-supervised/supervisor \
  --timeout 5400 --interval 1 --sample-clocks -- \
  python3 tools/integration/mtp_cancel_state_parity.py \
  --config bench/results/2026-10-13-phase5-q2-accepted-prefix/server-config-with-mtp.json \
  --output bench/results/2026-10-12-phase5-q2-cancel-mtp-8chunks-supervised/run \
  --cancel-chunks 8 --reference-repeats 3 --fixed-expert-cache 3000
```

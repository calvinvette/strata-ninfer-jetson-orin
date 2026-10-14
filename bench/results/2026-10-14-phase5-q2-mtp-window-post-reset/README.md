# Q2_0 accepted-prefix parity after MTP reset: 512-token prompt

This is a focused Phase 5 state-correctness check after resetting the MTP
drafter's private sequence state at fresh request boundaries. It compares MTP
off and windows 2/3/4 in separate fresh services. It is not an end-to-end
performance, broad quality, or same-service recovery claim.

The Orin run used the Qwen3.8-Flash-Next GSQ RCO Q2_0 artifacts, FP16 KV,
8K configured context, 3,000 expert-cache slots, prefill chunk 512, and one
exact 512-token prompt with 64 generated tokens. Each arm ran with prompt cache
6, CPU prefill sharing disabled, adaptive swaps disabled, and the same
supervised 28-GiB cgroup limit. The prompt SHA256 is
`ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`; the
candidate service binary SHA256 is
`e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`.
The reused config SHA256 is
`adb1151b3e4dfc4b81765de73cb90d95098c8787479ace1be46d2cb12e38c7e8`.
Model files remained under `~/models`.

All four arms emitted identical 64-token IDs and matched all nine recorded
main-model persistent-state fields at final state. Every shared accepted-prefix
boundary matched: 38 for MTP2, 31 for MTP3, and 27 for MTP4. The corresponding
draft offers/acceptances were 37/26, 60/33, and 78/37. The supervisor passed
after 279.2 seconds. Minimum physical host availability was 16.89 GiB and
minimum admission availability was 8.50 GiB. Peak sampled scope usage was
19.50 GiB; sampled cgroup low/high/max/OOM/OOM-kill counters were zero. Swap
used peaked at 1.76 GiB. Clocks were observed dynamically; EMC clock reads
were denied, and request energy was not measured. Single-run timing fields in
`run-512-token-prompt/results.json` are retained for context only and do not
support a performance claim.

This confirms accepted-prefix state parity for this prompt, artifact, cache,
and KV configuration on the post-reset binary. It does not establish parity
for other workloads or formats, same-service recovery after cancellation, or
that the reset fix resolves adaptive-residency state drift.

## Reproduction

From the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-q2-mtp-window-post-reset/supervisor-run1 \
  --timeout 2400 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-14-phase7-q2-recall/config-8192-mtp4.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-14-phase5-q2-mtp-window-post-reset/run-512-token-prompt \
  --tokens 64 --prompt-tokens 512 --windows 0 2 3 4 --run
```

Per-arm engine logs, state traces, supervisor samples, and tegrastats are
retained under this directory. `SHA256SUMS.txt` covers the evidence files.

# Q2_0 8K-prompt MTP4 decode-cancellation state check — Orin — 2026-10-14

This extends the short-prompt accepted-prefix cancellation test to a held-out
near-limit retrieval prompt. The exact user text rendered to 7,498 tokens under
the local tokenizer. The service used the current candidate binary, Q2_0 native
pack, 8,192 context, FP16 KV, 3,000 expert slots, MTP4, accepted-only expert
adaptation at cadence 4, and no CPU prefill sharing. Cancellation occurred
after four nonempty stream deltas. Two fresh services then generated exactly
the six committed tokens from the same prompt, and the canceled service handled
a short recovery request.

The canceled request committed six tokens at accepted-prefix lengths 7,498,
7,500, 7,501 and 7,503. Both exact-length references matched its token IDs and
all 11 recorded persistent-state fields (`gdn`, `ple`, `tail`, `dead`,
`pooled`, `pooled_full`, `kv`, `mtp`, `stale`, `ple_prev`, and sequence
length) at all four shared boundaries; the references also matched each other.
The same service recovered with the exact response `Hello Orin!` and remained
alive. This is state-parity and recovery evidence, not a latency result or a
general quality claim.

The campaign ran sequentially under `MemoryMax=28G` and the six-GiB guard.
Minimum host availability was 16.86 GiB and minimum effective admission
availability was 6.76 GiB. Sampled cgroup pressure, limit and OOM counters
remained zero. The tested candidate binary SHA256 was
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`; the
prompt SHA256 is
`30ec98f48a6861fe1273147cf17763e730e8eec10c1d2e6022801d4ca0eb7997`.
Clocks were dynamic and energy was not request-attributed.

The first attempt is retained under `run/` and `supervisor/`, but is excluded:
the harness requested its default 1,024-token output allowance, which could
not fit after the 7,498-token prompt in an 8K context, so API admission rejected
the request before inference. The rerun used an explicit 48-token allowance
and passed. The harness now supports exact prompt files and explicit output
allowances; its focused tests pass 9/9, and integration Python discovery passes
136/136.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output bench/results/2026-10-14-phase5-q2-mtp8k-cancel-state-parity/supervisor \
    --timeout 2400 --interval 1 -- \
    python3 tools/integration/mtp_cancel_state_parity.py \
      --config bench/results/2026-10-14-phase7-q2-recall/config-8192-mtp4.json \
      --output run --cancel-chunks 4 --reference-repeats 2 \
      --fixed-expert-cache 3000 --max-output-tokens 48 \
      --prompt-file bench/results/2026-10-14-phase5-q2-mtp8k-cancel-state-parity/prompt.txt
```

Raw request, engine and supervisor records are retained in `run-retry1/` and
`supervisor-retry1/`; the exact prompt is `prompt.txt`. `SHA256SUMS.txt` covers
the report and retained evidence. Phase 5 remains open for other cancellation
positions, MTP windows, KV formats, task quality and graph-lifetime checks.

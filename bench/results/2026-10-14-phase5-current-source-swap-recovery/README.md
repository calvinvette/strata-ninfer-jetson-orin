# Current-source adaptive-swap recovery diagnostic — Orin — 2026-10-14

This repeats the accepted-only short/long/short sequence on current native
binary `e84dc9af72bd46ceb1f6fc1643aa5b97cd8c6fbf815b99b8163092806c84da9c`.
The Qwen3.8-Flash-Next Coder IQ1_M setup compared MTP off and window 4 in
separate fresh services. Each service processed the same 512-token prompt, the
2,048-token incident prompt, then the 512-token prompt again, with 16 generated
tokens per request, a 3,903-slot cache and accepted-only adaptation every four
committed tokens. Exact prompt identities are retained in `trace/results.json`.

Both services completed without a process or memory failure, but the equality
gate failed. MTP-off and MTP4 produced identical outputs and all nine
persistent fields request-by-request. Within each service, however, the first
and final short outputs differed at 14 of 16 token positions and their
persistent states differed. Each service recorded 12 adaptive choice batches
(1,090 expert replacements) and nine applied updates. The 28-GiB supervisor
retained 13.28 GiB minimum host availability and 9.58 GiB minimum admission
availability; sampled cgroup pressure and OOM counters were zero. The runner's
`status: fail` reflects the intended parity assertion, not a crash or pressure
abort.

The paired [delayed-swap control](../2026-10-14-phase5-current-source-swap-recovery-delayed/README.md)
used the same binary, prompts and sequence with adaptation cadence 100,000. It
recorded no adaptive choice or apply events and passed first-versus-recovery
output and state equality for both MTP settings. This supports swap-associated
recovery sensitivity on this configuration. It does not identify the affected
expert arithmetic, rule out cache-history effects, or establish task-quality
impact. No serving setting or default changes from this diagnostic.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-current-source-swap-recovery/supervisor \
  --timeout 7200 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/same_service_short_long_short.py \
  --config-dir bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7 \
  --workloads bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/workloads.json \
  --output bench/results/2026-10-14-phase5-current-source-swap-recovery/trace \
  --tokens 16 --adapt-every 4 --trace-adapt-choices
```

Raw service traces and supervisor samples are retained here.
`SHA256SUMS.txt` verifies them.

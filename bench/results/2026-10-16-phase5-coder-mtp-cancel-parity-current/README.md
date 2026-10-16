# Coder IQ1_M MTP cancellation and state parity — Orin — 2026-10-16

This supervised Phase 5 check canceled one streamed MTP request on the exact
Coder IQ1_M path, then compared every committed accepted-prefix state with
three fresh, exact-length references. Same-process recovery was also checked.

The target model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`,
revision `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. Its two GGUF shard
hashes are retained in [`inputs.json`](inputs.json). MTP came from the upstream
base checkpoint `Qwen/Qwen3.8-Flash-Next` revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`, converted into the existing local
`mtp/rt` runtime files. Their hashes are also in `inputs.json`; this result
identifies the exact Coder-plus-base-MTP pairing and does not claim a
Coder-specific MTP checkpoint.

The current candidate service binary SHA256 was
`c07cf3f634788d055316cbf345a2fa17dd66449cb5ddd8690781dbbd72403c88`; source
code was at commit `0464d128`, with repository HEAD `e833807c` during the run.
The tested profile used MTP window 4, accepted-only adaptation every four
accepted tokens, 3,000 requested expert-cache slots, FP16 KV, and an 8,192-token
context. The prompt asked for integers 1 through 1,000 separated by spaces,
with no introduction or conclusion.

The stream was closed after eight non-empty text deltas (`1 2 3 4 `). The engine
had committed 12 tokens across four verifier commits, at accepted-prefix
lengths `L=48, 51, 55, 59`. The same service then returned the exact recovery
response `Hello Orin!`. Each of three fresh references generated exactly 12
tokens; their token IDs matched the canceled stream and each other. All 11
persistent-state fingerprints matched at all four shared prefix lengths,
including GDN, PLE, KV, MTP draft state and stale state. All three reference
runs passed.

The run lasted 118.3 seconds under `MemoryMax=28G`. Across 114 one-second
samples, minimum host/admission availability was 13.26/11.08 GiB, above the
six-GiB host floor. Maximum leaf-cgroup `low`, `high`, `max`, `oom` and
`oom_kill` event counts were zero. CPU/GPU clocks were observed dynamically;
EMC readback was denied and energy was not request-attributed. This is a
correctness result for one cancellation point and one model/profile pairing,
not a performance or broad quality claim. Phase 5 remains open for other
windows, prompts, KV formats, cancellation positions and graph interactions.

Reproduce on Orin1 from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-16-phase5-coder-mtp-cancel-parity-current/supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 tools/integration/mtp_cancel_state_parity.py \
  --config bench/results/2026-10-15-phase7-current-source-coder-iq1m/config-8192.json \
  --output bench/results/2026-10-16-phase5-coder-mtp-cancel-parity-current/run \
  --cancel-chunks 8 --reference-repeats 3 --max-output-tokens 1024
```

The full accepted-prefix traces, per-reference comparisons, server configs,
engine logs, telemetry and supervisor result are retained here. The harness's
nine focused unit tests also pass.

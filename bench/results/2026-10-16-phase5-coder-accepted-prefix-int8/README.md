# Coder IQ1_M accepted-prefix state parity with INT8 KV — Orin — 2026-10-16

This supervised correctness check compared MTP off with MTP4 on exact 512-
and 2,048-token prompts and the same cadence-4 accepted-only adaptive update
policy as the FP16-KV cells in
[the paired state report](../2026-10-16-phase5-coder-accepted-prefix-adaptive/README.md).
INT8 KV was the only changed profile factor. Each arm used a fresh sequential
engine and generated 32 tokens; prompt-cache capacity was configured, but no
prompt tokens were reused.

The output token IDs were identical. Final persistent-state fingerprints
matched in every recorded field, and the accepted-prefix trace matched at all
17 shared commit boundaries (generated lengths 1, 3, 4, 7, 8, 11, 12, 16, 18,
20, 23, 24, 28, 29, 30, 31 and 32). MTP4 offered 27 drafts and accepted 15.
On the 2,048-token prompt, all 16 shared commit boundaries also matched; MTP4
offered 31 drafts and accepted 16. This adds INT8-KV state parity at both
prompt lengths. It is not a task-quality or performance result, and does not
qualify other prompts, contexts or adaptive migration behavior.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M,
pinned at revision `5348543e0147355ac9cbcb031184a3546350988e`. Shard hashes are
in `model-sha256.txt`. MTP uses the separate base checkpoint
`Qwen/Qwen3.8-Flash-Next`, revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`; runtime component hashes are in
`mtp-runtime-sha256.txt`. Model and runtime files remained under
`~/models/strata-orin-validation/`.

Both arms used service binary SHA256
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`; the
repository HEAD at run time was `78d03268191546cddf29fa69588f21c5583fd928`.
The configuration and binary identity are retained in `config.json` and
`run/results.json`.

The 512-token comparison passed its 28-GiB supervisor in 108.64 seconds, with
13.48 GiB minimum host/admission availability. The 2,048-token comparison
passed in 222.33 seconds, with 13.35 GiB minimum host/admission availability.
Both stayed above the six-GiB floor; sampled cgroup `low`, `high`, `max`, `oom`
and `oom_kill` events remained zero. Clocks remained dynamic; energy was not
attributed to the requests.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  /home/calvin/.local/python/bin/python3 tools/integration/run_control.py \
  --output bench/results/2026-10-16-phase5-coder-accepted-prefix-int8/recheck-supervisor \
  --timeout 1200 --interval 1 -- \
  /home/calvin/.local/python/bin/python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-16-phase5-coder-accepted-prefix-int8/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-16-phase5-coder-accepted-prefix-int8/recheck \
  --tokens 32 --prompt-tokens 512 --windows 0 4 --kv-format int8 \
  --use-config-adaptive-swaps --run
```

Repeat with distinct output paths and `--prompt-tokens 2048` for the longer
prompt. Raw token/state traces and supervisor samples are under `run/`,
`run-2048/`, `supervisor/` and `supervisor-2048/`. Phase 5 remains open.

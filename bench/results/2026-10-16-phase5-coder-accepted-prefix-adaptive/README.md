# Coder IQ1_M accepted-prefix state parity with adaptive updates — Orin — 2026-10-16

This supervised correctness check compared MTP off with MTP4 using the exact Coder IQ1_M GGUF snapshot already used in the Phase 7 Coder report. It retained the campaign's cadence-4 accepted-only adaptive update policy, used exact 512-token and 2,048-token formatted prompts, and generated 32 tokens in a fresh sequential engine for each arm and prompt. Prompt-cache capacity was configured, but the one-request-per-engine design reused no prompt tokens.

The responses were identical at all 32 token positions on both prompts. Final persistent-state fingerprints matched in every recorded field. The 512-token prompt matched at all 17 shared commit boundaries (generated lengths 1, 3, 4, 7, 8, 11, 12, 16, 18, 20, 23, 24, 28, 29, 30, 31 and 32); MTP4 offered 27 drafts and accepted 15. The 2,048-token prompt matched at all 15 shared commit boundaries; MTP4 offered 30 drafts and accepted 17. This is direct state parity evidence for these prompts and configuration; it is not a task-quality or performance result, and does not remove the route-dependent state failures found with the experimental CPU Q8_1 path.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M, pinned at revision `5348543e0147355ac9cbcb031184a3546350988e`. Its GGUF shard hashes are in `model-sha256.txt`. MTP uses the separate base checkpoint `Qwen/Qwen3.8-Flash-Next`, revision `de4b8e4d43b917e7706784d8bb445c9af86a3540`; runtime component hashes are in `mtp-runtime-sha256.txt`. Model and runtime files remained under `~/models/strata-orin-validation/`.

Both prompts used service binary SHA256 `dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`; the repository HEAD at run time was `2b016e0c1586306d54df4ab2e423b842da19c966`. The service configuration and binary hash are recorded in each `run*/results.json`.

The 512-token comparison passed its 28-GiB supervisor in 111.54 seconds, with 13.15 GiB minimum host/admission availability. The 2,048-token comparison passed in 207.97 seconds, with 13.35 GiB minimum host/admission availability. Both stayed above the six-GiB floor; sampled cgroup `low`, `high`, `max`, `oom` and `oom_kill` events remained zero. Clock settings were left dynamic; energy was not attributed to these requests.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  /home/calvin/.local/python/bin/python3 tools/integration/run_control.py \
  --output bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/recheck-supervisor \
  --timeout 1200 --interval 1 -- \
  /home/calvin/.local/python/bin/python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/recheck \
  --tokens 32 --prompt-tokens 512 --windows 0 4 \
  --use-config-adaptive-swaps --run
```

Repeat with distinct output paths and `--prompt-tokens 2048` for the longer prompt. The retained `run/` and `run-2048/` results include generated token sequences, all state fingerprints and shared-prefix comparisons. `supervisor/` and `supervisor-2048/` hold one-second physical-memory samples, cgroup data and tegrastats. This adds two adaptive accepted-prefix parity cells; Phase 5 remains open.

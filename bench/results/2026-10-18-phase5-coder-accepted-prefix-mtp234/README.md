# Coder IQ1_M MTP accepted-prefix state parity — Orin — 2026-10-18

This supervised Phase 5 correctness matrix compared MTP off/2/3/4 with accepted-only adaptive expert usage on the Coder IQ1_M artifact at exact 512- and 2,048-token formatted prompt lengths. Each isolated service generated 16 tokens. The independent comparison checked output IDs and persistent main-model state at every shared committed-token boundary, as well as final state and draft counters.

All six MTP arms passed: output IDs and persistent-state fingerprints matched the MTP-off reference at every shared boundary and at completion. At 512 tokens, accepted/offered drafts were 6/7, 7/8 and 8/11 for MTP2/3/4, with 10, 9 and 8 shared boundaries. At 2,048 tokens, counts were 5/7, 7/10 and 8/13, with 11, 9 and 8 shared boundaries. This strengthens accepted-prefix evidence across all planned MTP window sizes and two prompt lengths for this exact model/runtime/policy. It does not establish task quality or a performance benefit, test other KV formats, or resolve the separate state divergence associated with active CPU/GPU expert migration.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, IQ1_M, pinned at revision `5348543e0147355ac9cbcb031184a3546350988e`; GGUF shard hashes are retained in `model-sha256.txt`. MTP uses the separately sourced base `Qwen/Qwen3.8-Flash-Next` revision `de4b8e4d43b917e7706784d8bb445c9af86a3540`; runtime hashes are in `mtp-runtime-sha256.txt`. The service binary SHA256 is `dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, built from repository commit `a13685c63c472d08ad7acd929aeb24b09d46e1f8`. Model/runtime assets remained under `~/models/strata-orin-validation/`.

Each prompt-length block ran sequentially under `MemoryMax=28G` and the six-GiB physical-memory guard. The 512-token block took 201.0 seconds and retained minimum host/admission availability of 13.23/9.93 GiB. The 2,048-token block took 380.4 seconds and retained 13.20/10.76 GiB. Cgroup low/high/max/OOM/OOM-kill counters stayed zero. Clocks were dynamic; energy was not attributed. Raw engine logs, results, memory samples, tegrastats and supervisor results are retained by arm.

The first 512-token wrapper invocation passed an extra `--` and failed before launching the test command. It is retained under `supervisor-512/` and excluded from all model conclusions. The corrected run is `supervisor-512-retry/`.

Reproduce from the repository root on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  /home/calvin/.local/python/bin/python3 tools/integration/run_control.py \
  --output bench/results/2026-10-18-phase5-coder-accepted-prefix-mtp234/recheck-supervisor \
  --timeout 1800 --interval 1 -- \
  /home/calvin/.local/python/bin/python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-18-phase5-coder-accepted-prefix-mtp234/recheck \
  --tokens 16 --prompt-tokens 512 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

Repeat with a distinct output and supervisor directory and `--prompt-tokens 2048`. `SHA256SUMS.txt` covers retained files in this result directory.

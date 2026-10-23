# Near-limit Coder MTP3 rejection and recovery — Orin — 2026-10-23

This current-source accepted-prefix probe compared MTP off with MTP window 3
on the Coder IQ1_M model. Each arm used one engine for three requests: an
exact 7,501-token prompt with 12 generated tokens, an eight-token continuation,
then an eight-token post-continuation recovery request. It captured token IDs,
accepted-prefix state fingerprints and request-level draft counters.

MTP3 offered/accepted 10/6 drafts initially, 6/4 in continuation, and 8/3
in recovery. It therefore rejected four drafts in the initial request and two
in the continuation before recovery. MTP-off and MTP3 generated identical
token IDs in all three requests. Main-model fingerprints matched at every
shared captured commit position: six initial, four continuation and five
recovery positions. Endpoint fingerprints also matched. MTP-only draft-buffer
fields are excluded from that main-model state contract.

The supervised run lasted 526.7 seconds, including process starts, model
loading and all three requests in both arms. Minimum physical and admission
availability were 13.283 GiB, above the preserved 6 GiB floor. Sampled cgroup
low/high/max/OOM/kill counters stayed at zero. Clocks were observed but not
controlled; EMC readback was denied and energy was not measured. This elapsed
time is not used as a performance comparison.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M; shard
hashes, the engine build revision and binary hash are retained. The probe
script revision/hash is separately recorded because it is Python harness code
and changed after the binary was built. The model and MTP runtime remain under
`~/models/strata-orin-validation/`.

The continuation probe's `--mtp-window {2,3,4}` option defaults to 4. Its
focused tests passed 7/7 and the full Python integration suite passed 170/170.
Reproduce with fresh output paths:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/phase5-coder-mtp3-long-supervisor --timeout 2400 \
  --interval 1 --sample-clocks -- \
  python3 tools/integration/mtp_continuation_probe.py \
  --config bench/results/2026-10-23-phase5-coder-mtp3-long-rejection-recovery/config.json \
  --engine build/integration/candidate/strata \
  --output /tmp/phase5-coder-mtp3-long-run --prompt-tokens 7501 \
  --initial-tokens 12 --continuation-tokens 8 --recovery-tokens 8 \
  --mtp-window 3 --require-rejection --run
```

This adds one near-limit MTP3 transaction case. It does not establish a long
adaptive chain bound, cancellation behavior or multi-live correctness; Phase 5
remains open.

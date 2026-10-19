# Current-source Coder IQ1_M MTP round-cost/state diagnostic — Orin — 2026-10-19

This Phase 5 diagnostic reran MTP off/2/3/4 on the current CUDA service binary
with an exact 2,048-token prompt, FP16 KV, cadence-4 accepted-only expert
updates and 16 generated tokens. All four arms used fresh services and the
same Coder IQ1_M pack and base Flash-Next MTP runtime. `STRATA_DECODE_TIMING=1`
records per-request verify, commit/emit and draft time per round; the accepted-
prefix trace records emitted and accepted draft tokens for every round.

Every arm passed: MTP windows 2/3/4 matched the MTP-off token IDs and persistent
state at every shared accepted prefix and at completion. Draft acceptance was
5/7 (71.4%), 7/10 (70.0%) and 8/13 (61.5%). Those arms emitted 16 tokens in
11, 9 and 8 rounds, respectively. The per-round emitted-token and accepted-
draft sequences are retained in `analysis.json` and the raw `results.json`.
Rejected draft counts (`offered - accepted`) were 2, 3 and 5. Each active-MTP
arm committed one target-produced correction/bonus token per verifier round;
the analyzer records that total separately from rejected draft proposals.

| MTP window | Rounds | Tokens per round (mean) | Verify ms/round | Draft ms/round | Commit/emit ms/round |
| ---: | ---: | ---: | ---: | ---: | ---: |
| Off | 16 | 1.00 | 126.44 | 0.00 | 693.85 |
| 2 | 11 | 1.45 | 157.19 | 9.78 | 733.44 |
| 3 | 9 | 1.78 | 162.83 | 19.04 | 733.31 |
| 4 | 8 | 2.00 | 183.05 | 28.36 | 730.71 |

The verify figure includes GPU-reach wait, per-layer host work and stage time;
the detailed breakdown is in `analysis.json`. The measurements are from a
state-traced diagnostic run and only 16 output tokens per arm, so they describe
this capture and do not estimate untraced speed or establish a useful MTP
window. No profile or default changed.

The Hugging Face model is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. The MTP runtime is the
separate base `Qwen/Qwen3.8-Flash-Next` revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`. The service binary SHA256 is
`6de7699cb94c2efb5a7634dcddfdfdf4625cd91511340f519d225dc1e861a3f3`, built
from repository commit `ebef974c83b0e7bb08645abeea1166120aed7f95`. All model
and runtime files remained under `~/models/strata-orin-validation/`.

One 28-GiB supervised run completed in 374.5 seconds. Across 356 samples,
minimum host/admission availability was 13.21/10.71 GiB, above the six-GiB
floor; all cgroup low/high/max/OOM/OOM-kill counters were zero. CPU/GPU clocks
were observed dynamically, EMC readback was denied, and energy was not
attributed.

Reproduce on Orin from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-19-phase5-coder-current-source-mtp-metrics/supervisor-2048 \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-19-phase5-coder-current-source-mtp-metrics/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-19-phase5-coder-current-source-mtp-metrics/run-2048 \
  --tokens 16 --prompt-tokens 2048 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

`config.json` adds only `STRATA_DECODE_TIMING=1` to the prior accepted-prefix
configuration. `analyze.py` joins timing lines, draft counters, per-round
accepted-prefix records and supervisor telemetry. Phase 5 remains open because
adaptive CPU/GPU migration still changes persistent state in the separate
fixed-residency investigation.

# Current-source Coder IQ1_M accepted-prefix MTP check — Orin — 2026-10-19

This Phase 5 regression reruns the Coder IQ1_M MTP accepted-prefix comparison
with the current CUDA service binary at a 2,048-token prompt. MTP off is the
reference; MTP windows 2, 3 and 4 use the same prompt, FP16 KV, cadence-4
accepted-only expert updates, model pack and draft artifacts. Each arm ran in a
fresh service and generated 16 tokens. The harness compared token IDs and
persistent main-model state at every shared commit boundary and at completion.

All three MTP windows passed. IDs and every compared state fingerprint matched
the MTP-off reference. The arms offered/accepted 7/5, 10/7 and 13/8 drafts for
windows 2/3/4, with 11, 9 and 8 shared commit boundaries. The exact prompt
token-ID digest was
`93cefb75fa4bb48eec0bcbf5771e06a6cce6bbad03c463df644fb45634b3dc15`.

The tested service binary SHA256 is
`6de7699cb94c2efb5a7634dcddfdfdf4625cd91511340f519d225dc1e861a3f3`, built
from repository commit `ebef974c83b0e7bb08645abeea1166120aed7f95`. The Coder
IQ1_M model is pinned at Hugging Face revision
`5348543e0147355ac9cbcb031184a3546350988e`; the base Flash-Next MTP runtime is
pinned at `de4b8e4d43b917e7706784d8bb445c9af86a3540`. Model/runtime files
remain under `~/models/strata-orin-validation/`.

The 28-GiB supervised scope completed in 372.2 seconds. Across 353 samples,
minimum host availability was 13.16 GiB and minimum admission availability was
11.36 GiB, above the six-GiB floor. All sampled cgroup low/high/max/OOM/OOM-kill
counters were zero. CPU/GPU clocks were observed dynamically; EMC readback was
denied and energy was not attributed. This confirms the current binary's MTP
accepted-prefix contract for this one prompt/profile. It does not resolve the
separate Coder adaptive CPU/GPU migration state divergence or establish a
performance/quality benefit; Phase 5 remains open.

Reproduce the supervised 2,048-token run from the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-19-phase5-coder-current-source-mtp-prefix/supervisor-2048 \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-16-phase5-coder-accepted-prefix-adaptive/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-19-phase5-coder-current-source-mtp-prefix/run-2048 \
  --tokens 16 --prompt-tokens 2048 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

Raw per-arm traces, state fingerprints, accepted-prefix comparisons and
supervisor telemetry are retained under `run-2048/` and `supervisor-2048/`.

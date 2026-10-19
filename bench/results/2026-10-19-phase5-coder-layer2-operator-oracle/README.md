# Coder layer-2 same-activation CPU/CUDA expert oracle — Orin — 2026-10-19

This operator diagnostic uses the retained current-source all-layer capture
from the Coder IQ1_M incident prompt. At verifier position 511/token 271, it
loads the recorded layer-2 `ffn_x` once and evaluates each of the seven
CPU-owned routed experts independently through Strata's native CPU expert path
and CUDA grouped expert kernel. The parity tool also evaluates an FP64
accumulation from GGUF-dequantized weights. That reference uses the pinned GGML
`to_float` codec decoders followed by independent FP64 products and sums; it is
independent of both production dot paths, but it is not an independent codec
decoder. The diagnostic does not use the service's router-weighted combine.

All seven experts use IQ2_S gate/up and IQ4_NL down weights. The CPU and CUDA
outputs differed in all 7,680 F32 values for every expert. Their relative-L1
difference ranged from 1.38% to 1.67%; CPU relative-L1 error against the
FP64 reference ranged from 1.18% to 1.41%, while CUDA ranged from 0.93%
to 1.11%. This confirms that a same-input CPU/CUDA expert arithmetic mismatch
also exists at layer 2. The retained layer-2 service capture already has
different input activations and router weights across arithmetic arms, so this
isolated result does not reconstruct the combined layer output, prove the
downstream persistent-state cause, or establish task-quality impact.

The source model is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. The captured input contains
2,560 F32 values and has SHA256
`863084edc13c3a66e8b6827d0df22bbe1fb18917617fa61d1e026665f628acec`. The
parity utility SHA256 is in `artifact-identity.json`. All model files remained
under `~/models/strata-orin-validation/`.

Each expert run had a fresh `MemoryMax=28G` scope, read-only clock sampling and
the six-GiB host-availability floor. Minimum host and admission availability
were both 24.51 GiB; cgroup low/high/max/OOM/OOM-kill counters remained zero.
No process energy was measured. EMC readback was denied. An initial supervised
attempt is retained as a failed setup cell: the parity utility's requested dump
directory had not yet been created, so it exited before numerical checks. The
successful rerun created that directory first. No numerical failure was
excluded.

Re-run the seven actual CPU-owned experts in the captured route, sequentially
on Orin:

```sh
for expert in 174 62 69 130 143 151 28; do
  systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
    bash bench/results/2026-10-19-phase5-coder-layer2-operator-oracle/run.sh "$expert" rerun
done
python3 bench/results/2026-10-19-phase5-coder-layer2-operator-oracle/analyze.py
```

The retained `analysis.json` is regenerated from per-expert parity output and
supervisor telemetry. `SHA256SUMS.txt` covers this report, analysis, route,
activation, command and telemetry artifacts. Phase 5 remains open: adaptive
migration has not been shown to preserve long-chain state or continuation.

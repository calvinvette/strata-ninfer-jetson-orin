# Mode-matched expert 118 CPU/GPU oracle

This oracle reuses the captured service activation for layer 16, position 515,
expert 118. It sets both `STRATA_EXP_MODE=0` and
`STRATA_NATIVE_CPU_Q8_1_DOT=all`, matching the adaptive service pair's CPU
arithmetic selector. The first oracle run omitted the CPU selector; its CPU
result remains in the sibling `expert118-oracle/` directory as a default-mode
control and must not be compared directly to this service row.

The mode-matched standalone CPU output agrees with the actual service CPU-pool
capture to maximum absolute difference 5.0e-11 and relative L2 9.51e-10. The
Q8_1 CPU and CUDA oracle outputs differ by 0.01352% relative L2. The
verifier-parts buffer is the actual mixed-owner per-expert data consumed by the
verifier's combine, not a CUDA-only oracle. A same-service cross-check in the
layer-40 follow-up matched direct CPU rows to this buffer within JSON
serialization precision.

The standalone oracle passed under the 28-GiB supervisor, with 24.51 GiB
minimum host/admission availability and zero cgroup memory events. No energy
or performance claim is made.

Reproduce with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-layer16-owner-layer17-state-position515/expert118-oracle-cpu-q8-1-all/supervisor \
  --timeout 1200 --interval 1 --sample-clocks -- \
  env STRATA_EXP_MODE=0 STRATA_NATIVE_CPU_Q8_1_DOT=all \
  build/integration/candidate/native_expert_parity \
  "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --expert 118 \
  --activation-f32 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-layer16-owner-layer17-state-position515/expert118-oracle/layer-16-expert-118-service-activation.f32 \
  --dump-f32-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-short-short-short-layer16-owner-layer17-state-position515/expert118-oracle-cpu-q8-1-all \
  16
```

The mode-matched output comparison is in `service-owner-compare.json`.

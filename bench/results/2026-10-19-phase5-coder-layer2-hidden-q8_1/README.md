# Layer-2 grouped IQ4_NL Q8_1 reduction fix — Orin — 2026-10-19

The opt-in CPU Q8_1 dot for Coder IQ2_S/IQ4_NL previously matched CUDA's
standalone `native_small_mmvq` four-warp reduction. The service uses the grouped
`native_down_multi_kernel` path, whose `row_dot_multi` assigns lane-strided
sub-blocks to one warp. On the captured layer-2 expert 174 activation, the old
mapping made CPU down-on-CUDA-hidden-state differ in 2,244 of 7,680 output
words. The changed CPU mapping follows the grouped service schedule; the same
check now has **0/7,680** output differences. The Q8_1 `d` scales and codes
match; only the unused stored `s` fields differ (60 bytes across 60 blocks).

The old standalone-kernel comparison still reports 789/2,560 different words
for this data because its four-warp reduction tree is a different contract.
It is retained as an informational diagnostic. The opt-in path is intended to
mirror the grouped service operation, and grouped service parity is now the
required result.

Three randomized, fixed-residency owner-placement pairs were rerun with the
corrected source on the pinned Coder IQ1_M model. Each pair used the same 512
prompt tokens and 3,007 cache slots, with seven layer-2 experts placed on CPU
in one arm and CUDA in the other. Across all pairs, all 16 accepted-prefix
state fingerprints, completion IDs, prompt-end GDN hashes and 16 captured
device-side layer-2 route records matched exactly. A separate raw GDN state
capture at the first accepted prefix (512 cells, 36 layers, 817,152 F32 values
per layer) was byte-identical across CPU and CUDA arms (SHA256
`6508db7802f792cdcf146f579c4eb9bbfa26fd6e7f41c0bb3b4a3aa90eca322b`). The
three-pair analysis is in `postfix-grouped-map-analysis.json`; the analyzer
rechecks the retained compressed GDN bytes, route identities, state records,
supervisor floors and cgroup events.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. Full GGUF shard hashes are
in `model-sha256.txt`. Models and expert packs remained in
`~/models/strata-orin-validation/`. The source build started at parent commit
`f25609823ec44089113c5d856dfc02f01ac5154e`; the exact two-file source diff is
`source-overlay.diff`, and source-file hashes are in `source-sha256.txt`.
The CUDA service binary SHA256 is in `binary-sha256.txt`.

All six Q8_1 dot/window CTests passed on Orin. The `native_expert_parity` and
`strata` CUDA targets rebuilt with one job. The exact updated CPU source and
parity target compiled and linked under HIP/ROCm 7.10.0a20251120 gfx1100 and
SYCL/oneAPI 2026.1.1 on maestro1; both CLI-help checks exited 0. See
`backend/maestro1/README.md` for hashes and logs. These are x86 build checks,
not GPU runtime qualification.

All service arms used `MemoryMax=28G`, one-second memory/clock supervision and
the six-GiB physical headroom floor. The minimum host and admission availability
in the three pairs were 15.915/15.915, 16.012/16.012 and 15.989/15.768 GiB.
Every supervisor passed and cgroup pressure/OOM counters remained zero. Clocks
were observed dynamically; EMC readback and process-attributed energy were
unavailable. This is correctness evidence for this opt-in operator, model,
prompt and fixed-residency pair. It is not a performance claim, default change,
quality qualification or Phase 5 closeout.

Reproduce the paired service check after preparing the existing profiles with:

```sh
OUTROOT=/tmp/layer2-grouped-map-paired-runs \
  BLOCKS=3 SEED=20261020 \
  bash bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/run_pairs.sh
OUTROOT=/tmp/layer2-grouped-map-device-route-pair \
  bash bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/run_device_route_check.sh
python3 bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/analyze_postfix.py \
  --root /tmp/layer2-grouped-map-paired-runs \
  --route-root /tmp/layer2-grouped-map-device-route-pair \
  --output /tmp/layer2-grouped-map-analysis.json
```

The complete raw service logs, state traces, routes, compressed telemetry and
failed initial diagnostic setup attempts are retained under the two
`postfix-grouped-map-*` directories. Recompute artifact hashes with
`sha256sum -c SHA256SUMS` from this report directory.

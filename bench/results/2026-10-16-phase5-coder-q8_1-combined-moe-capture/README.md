# Coder IQ1_M weighted-combine capture — Orin — 2026-10-16

This supervised randomized pair extends the CPU-row diagnostic through the
verifier's layer-1 weighted combine. Both arms used the exact
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` repository at snapshot
`5348543e0147355ac9cbcb031184a3546350988e`, specifically its IQ1_M shards.
The default GGML CPU route ran second; the opt-in CUDA Q8_1 mirror ran first.
Both used the same current-source binary, prompt token hashes, expert-cache
configuration, MTP2, cadence-4 accepted-only adaptation, and swap budget 8. This is a
correctness diagnostic, not a timing comparison.

The model shard SHA256 values are `e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad`
for shard 1 and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`
for shard 2. Both arms used binary SHA256
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`.

The existing `STRATA_VERIFY_DUMP_GDN_LAYER=1` diagnostic captured the
`STGDIAG4` `ffn_y` values after the layer-1 MoE weighted combine and shared
expert addition. Each arm captured 64 rows. There were 50 rows with the same
position and input token across arms; none of those combined outputs matched
bit-for-bit. The first shared row was position 511/token 271: all 2,560 output
values differed, maximum absolute delta was `2.1168e-4`, and relative L1
against the default output was `0.0040171`. Fourteen later input rows had
different tokens and were not treated as matched arithmetic inputs.

The paired route trace separately captured dispatch 1393/layer 1. Its input
activations, ten expert IDs, and owner choices matched between arms. CPU-owned
experts 209, 207, 85 and 153 differed in all 2,560 output values, with relative
L1 deltas `0.012306`, `0.015658`, `0.012738` and `0.013444`. The diagnostic
streams do not yet establish a direct row-by-row join between that dispatch
and the verifier's 64 combined-output rows, so these results localize a route
change before combine and show combined-output differences in the same paired
service, without claiming that the selected dispatch alone caused the first
combined-output delta.

All four requests returned 16 tokens. Default and mirror outputs matched on
the first short request and the immediate recovery request, differed at 3/16
positions on the long request, and differed at 13/16 positions on the next
short continuation. Persistent-state fingerprints differed between arms for
each request. Both supervisors passed; minimum host/admission availability was
14.433 GiB for default and 14.229 GiB for the mirror across 193 and 194
one-second samples. Cgroup low/high/max/OOM counters remained zero. The six-GiB
headroom floor was met. Energy was not attributed, and EMC clock sampling was
unsupported because access to the Tegra debugfs clock path was denied.

The captured combined output demonstrates a service-level numerical change at
the post-combine boundary. It does not establish a quality fix, accepted-state
parity, an end-to-end performance win, or a direct causal join to dispatch
1393. Phase 5 remains open.

Reproduce the pair and summary with:

```sh
/usr/bin/python3.10 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/run_trace_pair.py \
  --seed 20261027 --capture-cpu-outputs --capture-combined-moe \
  --output bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture/reproduction

python3 bench/results/2026-10-16-phase5-coder-q8_1-first-divergence-trace/analyze_combined_moe.py \
  bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture/reproduction/default/result/combined-moe.bin \
  bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture/reproduction/cuda_mirror/result/combined-moe.bin \
  --default-service bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture/reproduction/default/result \
  --mirror-service bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture/reproduction/cuda_mirror/result \
  --output bench/results/2026-10-16-phase5-coder-q8_1-combined-moe-capture/reproduction/combined-output-analysis.json
```

The original weight files remain under `~/models/`; this report retains
captured numeric outputs, service logs, request results and supervisor
telemetry only.

# Q2_0 short-prefix persistent-state sweep

This diagnostic asks whether the previously observed Strata CPU-miss versus
strict-NInfer state mismatch appears only near the end of a 2K prompt. Three
exactly tokenized prefixes (512, 1,024 and 1,536 tokens) were made from the
same synthetic retrieval fixture. Each backend processed the same prefix with
the existing 6-GiB staged-residency configuration and one generated token.
The CPU-miss arm used the expert-ID-filtered Q8_1 mirror for Q2_0/Q2_0 at model
layer 0, experts 83, 88, 90 and 109; the other arm used strict NInfer staging.
Final GDN arrays were compared with `compare_gdn_state_dumps.py`.

| Prompt tokens | Token IDs match | Final persistent state | GDN global rel. L2 | GDN ordinal 2 / model layer 2 | Ordinal 3 / model layer 4 | Ordinal 4 / model layer 5 | Minimum available memory |
| ---: | :---: | :--- | ---: | ---: | ---: | ---: | ---: |
| 512 | yes | differs: GDN, tail, pooled, pooled-full, KV | 0.03431 | 3.37e-9 | 2.46e-5 | 3.23e-3 | 11.43 GiB |
| 1,024 | yes | differs: GDN, PLE, tail, pooled, pooled-full, KV | 0.03098 | 1.21e-9 | 6.93e-5 | 1.97e-3 | 11.50 GiB |
| 1,536 | yes | differs: GDN, PLE, tail, pooled, pooled-full, KV | 0.04960 | 1.30e-9 | 1.79e-9 | 1.64e-9 | 11.52 GiB |

GDN `ordinal` is the comparator's index among GDN blocks, not a model-layer
index. Ordinals 0–2 map to model layers 0–2; ordinal 3 maps to model layer 4
and ordinal 4 to model layer 5. At 512 and 1,024 tokens, the first ordinal
above `1e-5` relative L2 is ordinal 3/model layer 4. At 1,536 tokens, ordinals
3 and 4 match to near floating-point noise; the first ordinal above `1e-5` is
ordinal 5/model layer 6. Thus the discrepancy is present well before a 2K
prefix, but its first visible GDN location is prompt-dependent. The 1,536
sample also shows why a single layer-5 capture cannot explain all state drift.

All runs returned exit code 1 because the checker correctly rejects the
persistent-state mismatch. The matching single output token is not a quality
pass. This sweep is neither a benchmark nor a task-quality test, and it does
not identify the originating operation. Minimum available/admission memory
was 11.43–11.52 GiB, above the preserved 6-GiB floor. GPU/CPU frequencies were
sampled read-only; EMC frequency was inaccessible. Energy was not measured.

The source workloads are in [`input/`](input/), and [summary.json](summary.json)
contains compact measurements and binary identity. Raw 118-MB GDN dumps,
engine logs and supervisor telemetry are local-only and are not checked in.

To reproduce a pair on Orin (replace `N` with 512, 1024 or 1536):

```bash
python3 tools/integration/run_control.py \
  --output /tmp/q2-prefix-N-supervisor --timeout 600 --interval 1 --sample-clocks -- \
  python3 tools/integration/ninfer_q2_retrieval_check.py \
    --config bench/results/2026-10-26-e6-q2-staged-retrieval-2k/evidence/config.json \
    --engine build/integration/e0-cuda-build/strata \
    --workload bench/results/2026-10-26-e6-q2-prefix-context-state-sweep/input/N.json \
    --output /tmp/q2-prefix-N-run \
    --compare-cpu-miss-staged --max-new 1 --dump-gdn \
    --cpu-q8-1-selector 'q2_0/q2_0@layer=0' \
    --cpu-q8-1-experts '83,88,90,109' --run
```

Compare the produced `cpu-miss.gdn.bin` and `ninfer-staged.gdn.bin` with
`python3 tools/integration/compare_gdn_state_dumps.py REFERENCE CANDIDATE`.

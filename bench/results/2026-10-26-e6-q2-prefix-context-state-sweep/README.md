# Q2_0 short-prefix persistent-state sweep

This diagnostic asks whether the previously observed Strata CPU-miss versus
strict-NInfer state mismatch appears only near the end of a 2K prompt. Three
exactly tokenized prefixes (128, 256, 512, 1,024 and 1,536 tokens) were made from the
same synthetic retrieval fixture. Each backend processed the same prefix with
the existing 6-GiB staged-residency configuration and one generated token.
The CPU-miss arm used the expert-ID-filtered Q8_1 mirror for Q2_0/Q2_0 at model
layer 0, experts 83, 88, 90 and 109; the other arm used strict NInfer staging.
Final GDN arrays were compared with `compare_gdn_state_dumps.py`.

| Prompt tokens | Token IDs match | Final persistent state | GDN global rel. L2 | GDN ordinal 2 / model layer 2 | Ordinal 3 / model layer 4 | Ordinal 4 / model layer 5 | First ordinal above 1e-5 | Minimum available memory |
| ---: | :---: | :--- | ---: | ---: | ---: | ---: | :--- | ---: |
| 128 | yes | differs: GDN, tail, pooled, pooled-full, KV | 0.06257 | 1.43e-9 | 3.84e-3 | 4.28e-3 | ordinal 3 / model layer 4 | 11.50 GiB |
| 256 | no | differs: GDN, tail, pooled, pooled-full, KV | 0.03871 | 1.09e-9 | 1.52e-9 | 3.78e-6 | ordinal 5 / model layer 6 | 11.50 GiB |
| 512 | yes | differs: GDN, tail, pooled, pooled-full, KV | 0.03431 | 3.37e-9 | 2.46e-5 | 3.23e-3 | ordinal 3 / model layer 4 | 11.43 GiB |
| 1,024 | yes | differs: GDN, PLE, tail, pooled, pooled-full, KV | 0.03098 | 1.21e-9 | 6.93e-5 | 1.97e-3 | ordinal 3 / model layer 4 | 11.50 GiB |
| 1,536 | yes | differs: GDN, PLE, tail, pooled, pooled-full, KV | 0.04960 | 1.30e-9 | 1.79e-9 | 1.64e-9 | ordinal 5 / model layer 6 | 11.52 GiB |

GDN `ordinal` is the comparator's index among GDN blocks, not a model-layer
index. Ordinals 0–2 map to model layers 0–2; ordinal 3 maps to model layer 4
and ordinal 4 to model layer 5. The 128- and 512–1,024-token prefixes first
exceed `1e-5` at ordinal 3/model layer 4. At 256 tokens, ordinal 4/model layer
5 is `3.78e-6` and the first ordinal above threshold is ordinal 5/model layer
6. At 1,536 tokens, ordinals 3 and 4 are near floating-point noise and ordinal
5 is the first above threshold. The discrepancy is present by 128 tokens, but
its first visible GDN location is prompt-dependent; it is not a monotonic
context-length effect.

For the 128-token prefix, a captured model-layer-2 MoE row at position 127 had
matching routes, `6.87e-8` input relative L2 and `1.00e-7` combined-output
relative L2. Four of ten expert rows differed slightly. At model layer 3,
routes still matched, but the captured MoE input was already `5.47e-4` relative
L2 apart; its combined output was `6.51e-3`. The model-layer-3 input is after
that block's QSA path. An opt-in residual-boundary capture found only
`5.50e-8` relative L2 difference at the post-read layer-3 input, while the
layer-3 MoE input was `5.47e-4` apart. The large change therefore appears after
the captured QSA input and before the layer-3 MoE, within the QSA
attention/residual path. QSA internals were not captured, so the operation
responsible is still unknown. At model layer 4, the captured GDN `x` was
already `4.37e-3` apart. Compact captures and metrics are listed in
[boundary-128](boundary-128.json).

All runs returned exit code 1 because the checker correctly rejects the
persistent-state mismatch. Four of the five prefixes had matching single
output-token IDs; the 256-token prefix differed. Matching one token is not a
quality pass. This sweep is neither a benchmark nor a task-quality test, and it does
not identify the originating operation. Minimum available/admission memory
was 11.43–11.52 GiB, above the preserved 6-GiB floor. GPU/CPU frequencies were
sampled read-only; EMC frequency was inaccessible. Energy was not measured.

The source workloads are in [`input/`](input/), and [summary.json](summary.json)
contains compact measurements and binary identity. Raw 118-MB GDN dumps,
intermediate captures, engine logs and supervisor telemetry are local-only and
are not checked in.

To reproduce a pair on Orin (replace `N` with 128, 256, 512, 1024 or 1536):

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

The 128-token layer-2→3 boundary capture uses the same command with
`--capture-boundary-layer 2 --capture-boundary-position 127`; compare the two
`cpu-miss.boundary` and `ninfer-staged.boundary` files using
`tools/integration/compare_boundary_capture.py`.

## QSA stage capture at model layer 3

An opt-in stage capture was added to inspect the QSA block on the 128-token
prefix at model layer 3, position 125 (token ID 271). The captured QSA input
relative L2 was `8.16e-8`; the query, current key and current value were exact.
Index-query relative L2 was `9.24e-8`. The selected block IDs were identical
(2,051 entries). At the attention output, relative L2 was `3.97e-5`, rising to
`5.41e-5` after gating and `8.32e-4` after projection. The exact post-read
input to the next MoE was `5.47e-4` apart, matching the independently captured
layer-3 MoE input result. This pins the amplification after QSA input and
through the attention path. Historical cached K/V contents and individual
attention arithmetic stages were not captured, so its precise source remains
unknown.

Both checker runs intentionally returned failure because final persistent state
differs (GDN, tail, pooled, pooled-full and KV), despite equal generated token
IDs. This remains numerical localization only, not a quality or performance
qualification. Minimum available memory was 11.47 GiB; EMC frequency was
inaccessible and energy was not measured. The CUDA build and QSA analyzer tests
passed. The updated verifier compiled and linked for HIP on maestro1; SYCL uses
its separate `sycl/src/core/verify.cpp` implementation, which was unchanged and
already up to date. maestro1 is compile evidence only. Raw `.qsa` captures and
supervisor logs remain local-only.

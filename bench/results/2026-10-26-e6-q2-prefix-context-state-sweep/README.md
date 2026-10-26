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
IDs. A follow-up opt-in cache capture decoded the 128 selected historical K/V
rows at this same layer and position. Across 65,536 values per side, 301 K and
341 V values differed; relative L2 was `3.91e-5` for K and `4.93e-5` for V.
An independent host FP64 replay of selected-cell attention matched each
engine's captured attention output within `1.97e-7` relative L2. Its predicted
cross-engine attention difference (`3.974187e-5`) matched the captured
difference (`3.974307e-5`) within `1.2e-9` relative L2. For this sample,
small historical K/V cache differences explain the measured attention delta;
the query and block selection match, and attention arithmetic is not a
material additional source at this boundary. This does not establish why the
historical cache rows first diverged or explain the later persistent-state
mismatch.

The paired checker still fails its persistent-state gate (GDN, tail, pooled,
pooled-full and KV) while token IDs and residency maps match. This is numerical
localization only, not quality or performance qualification. Minimum available
memory was 11.33 GiB; EMC frequency was inaccessible and energy was not
measured. The cache-capture run completed in 64.2 seconds. The final Orin CUDA
build passed; maestro1 HIP `strata` and SYCL `strata_engine` compile/link targets
also passed after rebuilding the shared QSA header and HIP implementation.
maestro1 provides x86 compile evidence only. Its SYCL runtime has no device, and
neither backend was executed there. Its first attempt
with cache capture always enabled hit the engine's 60-second no-progress
watchdog and is excluded; the separate opt-in retry completed. Raw `.qsa`,
`.kv` captures and supervisor logs remain local-only.

## Upstream trace at position 123

A follow-up captured model-layer-0 MoE rows at positions 122–125. At position
123 (token 198), both arms had bit-identical layer-0 input, routes, all ten
expert rows and combined output. The layer-1 GDN batch capture then showed only
floating-point-scale drift at its output (`3.50e-8` relative L2 for `y` and
`2.84e-8` for the feed-forward output). At model layer 2, position 123, the
MoE input differed by `5.28e-8` relative L2 and route IDs were identical; the
largest route-weight change was about `1.5e-8`.

Only rank 4, expert 114, had a material layer-2 expert-row difference: 2,268
of 2,560 values, relative L2 `6.68e-4` (unweighted row). The combined layer-2
MoE output differed by `3.24e-5` relative L2. An independent FP64 Q2_0×Q8_1
expert oracle quantized both captured layer-2 inputs to the same Q8_1
activation and produced identical output hashes. The NInfer-staged service row
matched that oracle to `5.84e-8` relative L2; the CPU-miss service row differed
by `6.68e-4`. This localizes the large position-123 perturbation to the
CPU-versus-staged expert arithmetic for expert 114, rather than its tiny input
or route-weight differences. It provides a plausible upstream source for the
later layer-3 QSA cache-cell-123 mismatch, though the cache-cell capture and
layer-2 oracle came from separate paired runs; the full persistent-state
failure is still not resolved or qualified. A second service capture reproduced
the layer-2 input delta, the expert-114 row delta and the combined-output delta
at the reported precision. The oracle was not rerun for this repeat.

The run used the same 128-token Q2_0 retrieval prefix and one generated token.
It returned exit code 1 on the expected persistent-state gate, completed in
63.1 seconds, and retained 11.27 GiB minimum available/admission memory. CUDA
clock sampling was read-only; EMC was inaccessible and energy was not measured.
The GDN batch flag was enabled through the run config. Raw layer captures,
oracle activation files and supervisor output remain local-only.

## Expert 114 CUDA operator check

The Orin `ninfer_q2_expert_parity` tool was run on model layer 2 / expert 114
using the captured CPU-miss activation (SHA256
`8c51b622ec40d3d14bedc3d55847215046c99f4be8e51d545d1b7fa9a8b8d5f8`) and its
independent FP64 Q2_0×Q8_1 reference. The standalone NInfer D3/D4 path failed
this activation: relative L2 `8.17e-3`, maximum absolute error `4.12e-4`.
This path is not qualified for dispatch. In the same tool, the grouped cache-slot
route used by the service matched Strata's grouped Q2_0/Q8_1 CUDA path exactly
for this expert activation and for the 3-, 64- and 128-token top-10 cases; all
coverage checks passed.

The grouped-path event-timed operator screen had seven interleaved blocks. For
one token, Strata median was `24.714 us` and NInfer `24.502 us` (ratio 0.991,
NInfer/Strata). For the ten-expert shapes, NInfer was slower: `1.110x` at 64
tokens (`4,379.156` vs `3,946.750 us`) and `1.123x` at 128 tokens
(`8,938.061` vs `7,958.131 us`). These are kernel-only operator measurements;
they omit request, cache and transfer costs and do not establish an end-to-end
gain. They show why the qualified grouped integration has not produced a
significant active-expert speedup: the one-token result is effectively tied,
larger grouped work regresses, and the standalone D3/D4 candidate fails the
numerical gate on this real activation.

The measured binary SHA256 was
`ec1d713c80aaeb266a8b4934d73faef8bac08692349b2d39db7f09c075811602` at source
commit `65b80be3`; the Q2_0 shard was the same local model used above. The
supervised run took 11.4 seconds and had 24.13 GiB minimum available/admission
memory. EMC was inaccessible and energy was not measured. This is a targeted
operator diagnostic, not the randomized E6 performance confirmation.

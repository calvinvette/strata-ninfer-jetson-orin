# Q2_0 long-prompt prefill chunk confirmation — Orin — 2026-10-15

This seven-block randomized confirmation checked whether the previously measured prefill-chunk effect on a 512-token task carries to a distinct 7,501-token retrieval task. Each of the 14 cells used a fresh service, a separate 512-token warmup, then one measured 7,501-token prompt with a 48-token cap. The workload naturally stopped at 36 output tokens. Q2_0, FP16 KV, MTP off, 8,192 context, 3,000 exact expert-cache slots, eight workers, disabled prompt cache, no adaptive swaps and no trace were held fixed; only prefill chunk 32 or 128 changed. Models and packs remained under `~/models/`.

All 14 measured responses used exactly 7,501 prompt tokens and 36 completion tokens and exactly returned `EARLY=COPPER-FERN-482, MIDDLE=NORTH-EMBER-619, LATE=SILVER-OTTER-357`. Every service admitted exactly 3,000 expert slots. The analyzer also validated successful supervisors, uncached prefill timings, telemetry and all seven paired blocks.

| Prefill chunk | Median request time | Median prompt rate |
| ---: | ---: | ---: |
| 32 | 673.8 s | 11.2 tok/s |
| 128 | 273.5 s | 28.0 tok/s |

Across the seven paired blocks, chunk 128 reduced total request time by a median 59.56% (paired block bootstrap 95% interval −59.62% to −57.50%). Prompt rate increased by a median 149.6%. All seven blocks favored chunk 128. This independently confirms the direction on this near-limit prompt and exact profile; it does not establish a general default. No setting changed.

Minimum host availability was 17.85 GiB and minimum effective admission availability was 6.11 GiB, above the six-GiB floor by 0.11 GiB. Cgroup high/max/OOM/OOM-kill counters remained zero. Dynamic GPU frequency ranged from 306 MHz to 1,300.5 MHz and CPU frequency from 729.6 MHz to 2,201.6 MHz. EMC readback was unsupported/permission denied. Energy was not request-attributed. The narrow admission margin limits this result to the tested cell and retained conditions.

`analysis.json` contains all per-block request timings, paired effects, telemetry minima and clock ranges. `artifacts.json` pins the service binary, source, model, tokenizer, input files and workload identities. `screen/` contains the two-cell one-request feasibility run. `block-01/` through `block-07/` contain the independent confirmation, including fresh-service telemetry and API outputs. Reproduce from the repository root under the same 28-GiB ceiling with:

```sh
out=/tmp/q2-prefill-long-confirm7
systemd-run --user --scope --collect -p MemoryMax=28G \
  bench/results/2026-10-15-phase6-q2-prefill-long-workload/run_screen.sh "$out/screen"
# Optional feasibility analysis is checked manually against exact output/capabilities.
systemd-run --user --scope --collect -p MemoryMax=28G \
  bench/results/2026-10-15-phase6-q2-prefill-long-workload/run_confirm7.sh "$out"
python3 bench/results/2026-10-15-phase6-q2-prefill-long-workload/analyze.py --root "$out"
```

The confirmation runner uses a separate 512-token warmup for each fresh service; this avoids warming on the measured long prompt. `SHA256SUMS.txt` covers retained inputs, raw cell outputs, telemetry and analysis. Phase 6 remains open for its other interactions and workload domains.

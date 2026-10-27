# Staged Strata versus NInfer compute screen

Date: 2026-10-26. Hardware: Jetson AGX Orin 32 GB, CUDA 12.6, SM87. Model:
Qwen3.8-Flash-Next GSQ RCO Q2_0, both GGUF shards, with the same Q2 PLE pack
and expert profile as the [E6 retrieval run](../2026-10-26-e6-q2-staged-retrieval-2k/README.md).
Shard SHA256 values are recorded in [`summary.json`](summary.json).

## Method

Three randomized process pairs compared the default Strata grouped expert
compute path with strict NInfer grouped compute. Both arms used
`--pcie-frac 1.0`, identical model/profile flags, a 3,000-slot cache, 6-GiB
resident budget, 3-GiB workspace reserve, 8K context, MTP-2, prefill 128 and
eight workers. The single natural-generation workload was `pp2048+tg128`
(2,048 prompt tokens and 128 generated tokens), sourced from the established
[paired API workload set](../2026-10-09-paired-api-controls/extension/block-3-workloads.json).
Each process included its warmup and one measured sample. No state hash or
trace was enabled.

All six processes passed API and token-count checks. Each pair had the same
3,000-slot residency map, and every measured response hash matched within and
across arms. The pair order was Strata/NInfer, NInfer/Strata, Strata/NInfer.
The table reports positive throughput changes as faster NInfer and negative
latency changes as faster NInfer.

| Pair | Prompt TPS: Strata → NInfer | Change | Decode TPS: Strata → NInfer | Change | Client TTFT change | Client total change | Output equal |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 1 | 46.9 → 47.8 | +1.92% | 8.8 → 9.0 | +2.27% | −1.92% | −1.99% | Yes |
| 2 | 48.7 → 47.3 | −2.87% | 8.6 → 8.9 | +3.49% | +2.85% | +1.23% | Yes |
| 3 | 47.2 → 48.1 | +1.91% | 8.9 → 8.8 | −1.12% | −1.81% | −1.12% | Yes |
| **Paired median change** |  | **+1.91%** |  | **+2.27%** | **−1.81%** | **−1.12%** | **3/3** |
| **Paired range** |  | **−2.87% to +1.92%** |  | **−1.12% to +3.49%** | **−1.92% to +2.85%** | **−1.99% to +1.23%** |  |

No metric reached the 5% screen threshold, so a seven-pair confirmation was
not triggered. The mixed changes do not show a useful end-to-end gain for
this shape. Three pairs with one measured sample each are screening evidence;
no confidence interval or generalization claim is made.

Minimum available physical/admission memory was 11.43 GiB, above the 6-GiB
floor; cgroup `high`, `max`, `oom` and `oom_kill` event counters stayed zero.
GPU clocks were observed dynamically from 306 to 1,300.5 MHz (per-process
medians 816–918 MHz); clocks were not changed. EMC clock readback was denied
and energy was not measured. Detailed per-pair metrics, hashes, clocks and
memory values are in [`summary.json`](summary.json); raw requests, engine logs,
supervisor samples and residency files remain local under this directory.

The service screen agrees with the operator screen: the active grouped NInfer
dispatch is functionally identical to Strata's grouped path, but neither the
64/128-token operator tests nor this 2K+128 request screen demonstrate a
repeatable 5% gain. This does not test CPU-miss versus staged-miss benefit.

## Reproduction

The runner accepts `--comparison staged-compute`; its default remains the
existing CPU-miss versus staged-NInfer screen. Re-run this exact screen with:

```bash
python3 bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/run_staged_workload_screen.py \
  --comparison staged-compute \
  --only-workload pp2048+tg128 \
  --pairs 3 \
  --out bench/results/2026-10-26-e6-q2-staged-compute-screen
```

The runtime binary SHA256 was
`44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`, from
source code commit `35051742ab28b6be669e6650064936d1dd899bd5` (the checked-out
tree at measurement time was `273612c22f805c6794bed91a6860cb264f769271`, with
no intervening `src/` or `include/` changes). The runner extension is commit
`b6be3cf9`; its SHA256 is
`9ecf0945e7a6727a4f8458183fa8d27a6cb9103abcc92c66e92ed4456b725407`.

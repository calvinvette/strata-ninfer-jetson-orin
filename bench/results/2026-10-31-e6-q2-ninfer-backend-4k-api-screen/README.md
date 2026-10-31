# Q2_0 NInfer backend API screen at 4K expert capacity

Date: 2026-10-31. Device: Jetson AGX Orin Developer Kit (SM87), CUDA 12.6. This recovers and publishes the completed three-pair, same-day campaign that compared the strict NInfer Q2_0 expert backend with the Strata expert backend. Both ran the same `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0` two-shard model, PLE pack, expert profile, 4,000-slot cache, 8K configured context, prefill chunk 128, MTP window 2, prompt cache disabled, PCIe staging disabled, 8 pool workers, 6 GiB resident budget, 3 GiB workspace reserve and 9 GiB host reserve. Only the expert-backend selection changed; NInfer was strict.

Each independent process did one warmup followed by one measured tokenizer-verified 512-token synthetic prompt and 64-token generation. The three pair orders were baseline→candidate, candidate→baseline, baseline→candidate. No trace was enabled. The source checkout was `dd88f3ef`. A binary hash was not recorded at run time; the present build was rebuilt later and its digest is not attributed to this campaign.

## Results

Positive paired advantage means higher throughput or lower latency. Intervals are 95% percentile intervals from bootstrap resampling of the three independent paired blocks; with three blocks these are screening estimates, not confirmation.

| Metric | Strata median | NInfer median | NInfer paired advantage (95% interval) |
| --- | ---: | ---: | ---: |
| Prompt throughput | 31.3 tok/s | 31.1 tok/s | −0.32% (−4.79%, +1.97%) |
| Decode throughput | 9.0 tok/s | 9.3 tok/s | +3.33% (0.00%, +14.46%) |
| First-visible TTFT | 16.56 s | 16.62 s | −0.29% (−4.65%, +2.51%) |
| Client total | 23.50 s | 23.23 s | +0.04% (−2.40%, +5.63%) |

All six processes passed and generated exactly 64 tokens. All measured response bodies had the same SHA256. This is a narrow deterministic workload consistency check, not a general quality evaluation. The decode median does not reach the 5% useful-effect threshold, and its interval includes zero. Seven-pair confirmation is not justified for this cell without a new performance hypothesis. The operator-only schedule variants do not alter this API conclusion.

## Resources and limits

Minimum process-sampled available host RAM was 9.23 GiB, above the preserved 6 GiB floor and separate 3 GiB workspace reserve. Maximum sampled swap was 1.94 GiB; OOM kills were zero. CPU observations ranged 729.6–2,201.6 MHz and GPU observations 306–1,300.5 MHz. EMC readback was denied; clocks remained dynamic and energy was not attributed. No clock or unrelated service settings were changed.

The compact per-pair measurements, response hashes, pass status, resource floor and intervals are in [`paired-summary.json`](paired-summary.json). Raw request logs and supervisor traces remain in `/tmp/e6-cache4000-api-screen/campaign-retry/`; prompts and completions are not committed.

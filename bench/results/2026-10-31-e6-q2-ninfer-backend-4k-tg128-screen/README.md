# Q2_0 backend comparison at 4K cache, pp512+tg128

Date: 2026-10-31. Device: Jetson AGX Orin Developer Kit (aarch64, SM87,
CUDA 12.6). This three-pair screening experiment compares strict NInfer with
Strata on the same held-out `NIMBUS-7319` retrieval workload. Both backends
used the Q2_0 model, 4,000 expert-cache slots, 8K configured context, prefill
chunk 128, MTP window 2, eight pool workers, adaptive swaps, the 6 GiB resident
budget and separate 3 GiB workspace reserve. PCIe staging and prompt cache were
off. The only server setting changed was `--expert-backend`; the NInfer arm
also used `--expert-backend-strict`. Neither experimental CTA nor exact-entry
kernel toggle was enabled.

Three independent process pairs used order Strata→NInfer, NInfer→Strata,
Strata→NInfer. Each process issued one warmup and one measured request. The
measured request had 512 prompt tokens and generated 128 tokens. All six
measured responses began with the exact answer `NIMBUS-7319`, had 128 tokens,
and shared the same response SHA256. This checks deterministic task agreement,
not broad answer quality. Each process completed successfully.

## Results

Positive advantage means higher throughput or lower latency. Intervals are
95% percentile bootstrap intervals over the three independent paired-process
effects (100,000 resamples); they are screening uncertainty only.

| Metric | Strata median | Strict NInfer median | NInfer paired advantage (95% interval) |
| --- | ---: | ---: | ---: |
| Prompt throughput | 23.1 tok/s | 22.7 tok/s | −1.30% (−10.37%, +0.43%) |
| Decode throughput | 7.9 tok/s | 7.9 tok/s | −1.27% (−5.95%, +2.53%) |
| First-visible TTFT | 22.41 s | 22.77 s | −1.24% (−10.52%, +0.79%) |
| Client total | 38.37 s | 38.90 s | −1.20% (−8.74%, +1.09%) |

No metric reached the preregistered 5% useful-effect screen. The medians lean
slightly toward Strata, while all three-pair intervals include zero. No
seven-pair service confirmation is warranted for this cell. This follow-up
does not transfer the 3K→4K cache-policy result to a NInfer-specific backend
benefit: cache size is fixed here and the two compute backends are compared
directly. The grouped exact-entry operator improvement remains an operator
result without a corresponding request-level win.

## Resources and limits

Minimum sampled available RAM was 9.51 GiB, preserving the six-GiB floor and
separate workspace reserve. Peak sampled swap was 2.47 GiB; sampled OOM kills
were zero. CPU observations ranged 729.6–2,201.6 MHz and GPU observations
306–1,300.5 MHz. EMC readback was denied. Clocks remained dynamic and energy
was not measured. Per-pair values, response hashes, binary/model identity and
resource fields are in [`paired-summary.json`](paired-summary.json). Raw
prompts and responses remain outside the repository.

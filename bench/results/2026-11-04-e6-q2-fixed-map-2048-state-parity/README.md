# 2K same-map accepted-prefix state comparison

Date: 2026-11-04. Hardware: Jetson AGX Orin, CUDA. Model: Qwen3.8-Flash-Next
Q2_0. This is a one-pair correctness diagnostic, not a timing comparison.

## Result

Strata and strict NInfer each served the same 2,048-token retrieval/arithmetic
fixture twice in one fresh process: once as harness warmup and once as the
measured request. Both requests in both processes returned the exact expected
47-token answer. The accepted-prefix token IDs and all recorded persistent-state
fingerprints matched at every committed output position across the two
backends, for both request ordinals.

Each request committed 47 generated tokens. The capture includes GDN, PLE,
QSA tail, pooled, KV, MTP, stale, dead, pooled-full and PLE previous-token
fingerprints. The learned 5,000-slot resident map was fixed, adaptation and
prompt caching were disabled, and both engines reported 47.7% expert-cache
hits (10,759/22,560 lookups). Strict NInfer reported a resident grouped Q2_0
dispatch. Minimum available memory was 8.69 GiB for Strata and 8.72 GiB for
NInfer, above the 6 GiB floor; sampled cgroup OOM kills were zero.

This closes the accepted-prefix state-parity gap for this exact short task and
fixed-map profile only. It does not address the previously observed long-prompt
state divergence, other workloads, or general semantic quality. The tracing
instrumentation materially slowed generation, so its prompt/decode/TTFT values
are excluded from performance evidence. Raw logs and full fingerprints remain
outside Git under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task2048-backend-statecheck-20261104/`;
[`evidence.json`](evidence.json) records hashes and the bounded result.

## Reproduction shape

Both arms used the same Q2_0 files, `learned-map.bin`, 5,000 GPU expert slots,
6 GiB RAM-resident expert budget, 8,192 context, prefill 128, MTP-2, eight
workers, prompt cache off, adaptation off, and no PCIe staging. The candidate
added `--expert-backend ninfer --expert-backend-strict`. Each arm was run
sequentially under `run_control.py`; `api_control_block.py` enabled
`--no-trace --accepted-prefix-trace --state-hash`. The first request was
warmup; the second was measured. No speedup is claimed.

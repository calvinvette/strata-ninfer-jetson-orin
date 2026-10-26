# Corrected-kernel 4K retrieval and state rerun

Date: 2026-10-25. The earlier 4,096-token Strata-versus-NInfer retrieval
comparison was repeated with the corrected grouped SwiGLU kernel. Both fresh
services returned the exact expected three codes and suffix sum in 47 tokens.
All token IDs and all nine final persistent-state fields matched.

| Metric | Strata | Strict NInfer |
| --- | ---: | ---: |
| Prompt tokens | 4,096 | 4,096 |
| Generated tokens | 47 | 47 |
| Prompt time | 90.839 s | 85.641 s |
| Decode time | 9.536 s | 9.710 s |
| Exact expected answer | pass | pass |
| Token IDs equal | yes | yes |
| Final persistent state equal | yes | yes |

This is one functional rerun, not a randomized performance comparison. Timing
values are recorded for reproducibility only. The Q2_0 model, 3,000-slot static
profile, 8K cap, FP16 KV, prefill 128 and eight workers were held fixed; only
the expert backend changed. The corrected service binary SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75`.
Full generated IDs/text, state hashes, arguments and service logs are in
[`results.json`](results.json) and this directory.

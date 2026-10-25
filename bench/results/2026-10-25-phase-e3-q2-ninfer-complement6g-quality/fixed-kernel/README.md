# 6-GiB held-out quality check after grouped SwiGLU correction

The same 512-token retrieval/arithmetic task was rerun with the corrected
NInfer kernel and the 6-GiB staged configuration. Both Strata and strict
NInfer returned the exact expected answer in 47 tokens. Generated token IDs
and all final persistent-state fields matched exactly. This clears the state
parity failure seen with the prior approximate division path for this tested
task and profile; it is not broad model-quality qualification.

| Metric | Strata | Strict NInfer |
| --- | ---: | ---: |
| Prompt tokens | 512 | 512 |
| Generated tokens | 47 | 47 |
| Prompt time | 31.896 s | 30.265 s |
| Decode time | 8.507 s | 8.733 s |
| Exact expected answer | pass | pass |
| Token IDs equal | yes | yes |
| Final persistent state equal | yes | yes |

Minimum available memory was 11.55 GiB, above the six-GiB physical headroom
floor and separate three-GiB workspace reserve. Full result and supervisor
telemetry are alongside this report.

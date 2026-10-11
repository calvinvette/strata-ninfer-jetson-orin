# CPU/GPU prefill-share state comparison — Orin — 2026-10-11

This correctness diagnostic compares fixed
`STRATA_PREFILL_CPU_SHARE=0` and `=0.5` on the same IQ1_M Coder model, Q2_0
MTP runtime, 512-token prompt, eight-worker pool, 4K context, prefill chunk 64,
and 6,519 admitted expert-cache slots. Both used candidate binary SHA256
`3ed52e6e0f845415b8fb2f2c15577f4b90efe49be72e2866d0dc961dbb0c95b0` at source
revision `51c0852`. Model digests and source identities are in the existing
[control manifest](../2026-10-11-phase4-gdn-prefill-share-control/model-artifact-identities.json). The measured request in each process
generated eight tokens; the same prompt was then used for a separate 64-token
extension. Both settings emitted identical token IDs and output text in these
short runs. No timing comparison is claimed.

At the first committed boundary (`L=512`, immediately after token ID 32), the
corrected numerical comparison differs in 28,587,171 of 29,417,472 GDN float32
values (97.18%). Relative L2 error against share-off is 3.172%, global RMS
absolute error is 0.008571, and the largest per-layer relative L2 is 5.713%
(GDN layer 26). The maximum element difference is 1.343 in layer 33. Every
accepted-prefix token ID matched across the eight-token requests, but their
full persistent-state fingerprints differ. The 64-token extensions also
matched all output token IDs and text SHA256, while accepted-prefix state
continued to differ through the final boundary.

The numerical dump was captured from the measured request after a distinct
172-token warmup. An earlier attempt used a 512-token warmup; because the dump
hook is one-shot at `L=512`, that attempt captured warmup state and is excluded
from the numerical result. Its raw request/log/telemetry remain in `share-0/`
and `share-0p5/`. The corrected compact analysis and all per-layer metrics are
in `analysis.json`; its values were reproduced with the standard-library-only
[`compare_gdn_state_dumps.py`](../../../tools/integration/compare_gdn_state_dumps.py).
The 117.7 MB GDN dumps remain local and are excluded from Git; their SHA256
values are recorded in `analysis.json`.

The corrected eight-token pair remained above the six-GiB physical floor with
8.39/8.42 GiB minimum availability. The 64-token extensions remained above the
floor with 8.41/8.44 GiB minimum availability. Both measured requests used the
same 6,519 cache slots. The longer runs show no output-token divergence through
64 generated tokens, but they do not identify which recurrent state is more
accurate or establish task-level quality. The measured fixed-share state
difference is consistent with the previously observed policy-dependent GDN and
QSA/KV state; it is not a quality pass. Keep the sharing mode experimental for
this model until held-out quality and broader state-drift bounds are established.

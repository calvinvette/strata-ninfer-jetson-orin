# E5 Q2_0 4K Strata-versus-NInfer retrieval regression

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. The same 4,096-token
held-out retrieval/scoring prompt was run in fresh services with MTP off and
identical model, cache, profile, context, prefill and worker settings. Only the
expert backend differed: default Strata versus strict NInfer.

Both arms returned the exact three codes and suffix sum in 47 tokens, with
identical token IDs. Their final persistent-state fingerprints differed in
GDN, tail, pooled, full pooled and KV. PLE, dead slots and previous PLE tokens
matched. This confirms the short-task state observation persists at 4K context;
it does not quantify the long-run numeric delta because this run captured state
fingerprints only.

Single-run prompt/decode times were 91.02/10.23 seconds for Strata and
88.58/10.24 seconds for NInfer. This was not randomized or repeated and is not
a performance estimate. Minimum physical/admission availability was
19,292,868,608 bytes (17.97 GiB), above the preserved 6 GiB floor. The
supervisor ran 233.6 seconds and reported zero exit-code success because the
state-parity assertion detected the expected cross-backend difference; the
workload itself returned exact text and token IDs. Energy was not attributed.

The exact result and supervisor summary are in [`evidence/`](evidence/).
The input fixture and exact-length generator are recorded in the [strict-NInfer
long retrieval report](../2026-10-25-phase-e5-q2-ninfer-long-retrieval/README.md).
This is one held-out 4K task, not general quality or performance qualification.

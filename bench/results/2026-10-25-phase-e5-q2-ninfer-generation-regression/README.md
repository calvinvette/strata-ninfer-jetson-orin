# E5 Q2_0 Strata-versus-NInfer natural generation check

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. Fresh MTP-off
services used the same Q2_0 model, PLE pack, tokenizer, expert profile, cache,
context, prefill chunk, workers and 512-token natural-language prompt. Only the
expert backend differed: default Strata versus strict NInfer.

Both arms generated 64 tokens. Their token sequences shared the first eight
tokens and first differed at generated token index 8 (the ninth token). Both
outputs were coherent continuations of the prompt, but the text and token IDs
were not identical. GDN, PLE, tail, pooled, full pooled, KV and previous PLE
state fingerprints also differed at the final boundary.

This is one natural-generation sample and does not establish a quality
regression or gain. It shows that exact text parity from the retrieval task does
not generalize to ordinary generation; quality needs its own held-out scoring
or human/judge protocol. No cross-backend state migration is qualified.

Prompt SHA256 is
`221e80cf324b2969ccf0b387a3093240af8a502c683f8c9bc7fbb159d447da05`; formatted
token-ID SHA256 is
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`. The
exact prompt, full generated IDs/text, state fingerprints and supervisor record
are in [`evidence/`](evidence/). The supervised run lasted 106.8 seconds and
retained at least 17.75 GiB physical/admission availability, above the 6 GiB
floor. All sampled cgroup low/high/max/OOM counters were zero. The state/token
parity checker returned nonzero after finding the divergence. Energy was not
attributed.

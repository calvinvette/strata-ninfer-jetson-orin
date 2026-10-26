# Corrected-kernel natural-generation parity rerun

Date: 2026-10-25. The previously divergent 512-token natural-generation
prompt was rerun twice with fresh sequential Strata-default and strict-NInfer
services after the grouped SwiGLU division correction. Both runs generated 64
tokens. Token IDs matched exactly between backends in both runs, as did all
nine final persistent-state fields. The generated token-ID SHA256 in both arms
and runs was
`b62790b6a2aaf2295adbecfb583d8372a1fbaf0b0639c5772e17d4d220c89342`.

The earlier pre-fix run first differed at generated token 9 and had divergent
state fingerprints. That observation remains valid for the old binary but no
longer reproduces on the corrected binary with this prompt/profile. This is
one deterministic prompt repeated twice; it does not establish broad natural
generation quality or numerical equivalence for other prompts.

The runs used the Q2_0 Coder model and PLE pack, 3,000 static expert slots,
8K context, FP16 KV, prefill 128, eight workers and MTP off. The corrected
service binary SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75`.
Prompt/decode times varied between the two non-randomized repetitions and are
not a performance estimate. Exact fixtures, request results, logs and launch
arguments are retained in this directory.

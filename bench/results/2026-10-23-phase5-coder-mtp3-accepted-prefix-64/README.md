# MTP3 accepted-prefix parity — Orin — 2026-10-23

The current candidate engine ran a deterministic 512-token formatted prompt and
64 generated tokens in two isolated private processes, MTP-off and MTP3. Both
runs produced identical token IDs. MTP3 offered 60 drafts and accepted 33.
The accepted-prefix trace recorded 31 shared commit boundaries; all nine
persistent-state fingerprints matched at every boundary and at final state:
GDN, PLE, tail, dead, pooled, pooled-full, KV, previous-previous-embedding,
and layer cursor (`L`). The comparison passed.

This probe establishes exact transaction parity for this prompt and 64-token
chain. The probe uses the harness's fixed-length deterministic context rather
than the retrieval prompt used in the adjacent performance confirmation. It
does not qualify adaptive state migration, longer chains, cancellation,
long-context state or multi-live decoding.

- Source HEAD at launch: `5bcae49a`.
- Device: Orin AGX, native aarch64, CUDA runtime path.
- Model: Coder IQ1_M with base-checkpoint MTP3 weights retained under
  `~/models/strata-orin-validation`.
- Formatted prompt token count: 512; generated tokens: 64.
- Prompt token IDs SHA256: `ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`.
- Full output, state trace, engine logs and engine binary hashes are in
  `results.json` and the two log files.

# MTP4 accepted-prefix state parity — longer chains — Orin — 2026-10-24

## Result

The current CUDA candidate ran the deterministic 512-token formatted Coder
IQ1_M prompt with MTP-off and MTP4, using FP16 KV and separate private
processes. This extends the earlier 64-token check to a 256-token fixed-length
chain and a second request with a 512-token allowance that ended at natural
EOS after 348 tokens.

| Requested generation | Actual output | MTP4 drafts / accepted | Shared accepted-prefix boundaries | Token IDs | Final state |
| ---: | ---: | ---: | ---: | --- | --- |
| 256 | 256 | 342 / 142 | 115, prefixes 1–256 | exact | all 9 fields exact |
| 512 | 348 (natural stop) | 468 / 194 | 157, prefixes 1–348 | exact | all 9 fields exact |

At every shared accepted-prefix boundary, all nine persistent-state fields
matched: `L`, GDN, PLE, tail, dead, pooled, pooled-full, KV and PLE previous
embedding. MTP-off and MTP4 produced identical token IDs and final state in
both runs. This is direct state evidence over one deterministic prompt and two
chain lengths; it does not qualify other prompts, KV formats, cancellation,
adaptive migration or multi-live batch state.

## Identity and resources

- Device: Orin AGX, native aarch64, CUDA 12.6 / SM87.
- Source HEAD: `78908314`; binary SHA-256:
  `ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`.
- Model: pinned Coder IQ1_M GGUF artifact revision
  `5348543e0147355ac9cbcb031184a3546350988e`, with base-checkpoint MTP
  weights under `~/models/strata-orin-validation/`.
- Formatted prompt token-ID SHA-256:
  `ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`.
- Minimum physical/effective-admission availability was 16.86 GiB for the
  256-token run and 16.90 GiB for the 512-token allowance. Both supervised
  runs retained the six-GiB floor. GPU clocks varied dynamically; EMC readback
  and energy were unavailable/not measured.

Compact token/state traces and supervisor results are retained in the adjacent
JSON files. Detailed engine logs and telemetry remain local. The earlier
[64-token MTP4 probe](../2026-10-24-phase5-coder-mtp4-accepted-prefix-64/README.md)
matched 29 shared boundaries (35/84 drafts accepted) on this same prompt.
Together, these are bounded uninterrupted MTP4 transaction checks, not a
Phase 5 closeout; multi-live state drift remains unresolved.

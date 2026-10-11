# Probabilistic MTP verifier scratch — Q2_0 Orin — 2026-10-11

The opt-in `STRATA_SPEC_PROB=1` route was exercised with the Q2_0 model and the existing MTP runtime under `~/models/strata-orin-validation/mtp/rt`. The request used prompt token `[32]`, temperature `1.0`, seed `20261011`, `--spec 4`, and a 12-token output limit. No model was downloaded or copied into the repository.

The engine reported probabilistic draft acceptance over 106,299 tokens, offered 21 drafts, accepted 6, and generated all 12 requested output tokens. The verifier allocated its 4,128-byte `verifier-aux-device` token/distribution scratch and freed it at shutdown. The trace balanced all 283 allocation/free events and ended with zero live requested bytes on both host and device. Minimum host `MemAvailable` was 15,765,237,760 bytes (14.69 GiB), above the preserved six-GiB floor. The deterministic seed and emitted IDs are retained in `run/results.json`; this one request qualifies the scratch owner lifecycle, not probabilistic quality or end-to-end performance.

The existing `spec_verify_parity`, `coupled_draft_test`, and `spec_prob_test` CTests passed after the runtime smoke. Minimum availability during that supervised set was 26,275,016,704 bytes (24.47 GiB); raw output is in the sibling [test report](../2026-10-11-phase3-spec-prob-tests/).

The [reproduction harness](../../../tools/integration/spec_prob_owner_smoke.py) requires the probabilistic mode log, at least one offered draft, an observed auxiliary owner, and balanced frees. The full supervised output and engine trace are in `result.json`, `stdout.txt`, `stderr.txt`, `tegrastats.txt`, `memory.jsonl`, and `run/`.

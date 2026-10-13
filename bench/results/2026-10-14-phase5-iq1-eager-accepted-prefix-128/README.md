# IQ1_M eager/captured accepted-prefix comparison — Orin — 2026-10-14

This follow-up repeats the [128-token captured accepted-prefix check](../2026-10-14-phase5-iq1-accepted-prefix-128/README.md)
using the same IQ1_M binary, 2,048-token incident prompt, 8K context, FP16 KV,
3,000 requested cache slots, prefill chunk 64, zero CPU-prefill sharing and
accepted-only adaptation every four published tokens. The only serving-route
change was `--no-capture`. Each arm used a fresh service; MTP windows were off,
2, 3 and 4. Model and MTP assets remain under `~/models/`.

MTP windows 2/3/4 each matched all 128 published IDs, final state and all
shared accepted-prefix states against MTP-off on the eager route (78, 74 and 58
boundaries). The same three windows offered/accepted 66/50, 89/54 and 120/70
drafts. Comparing the captured and eager traces directly also found identical
published IDs, final state and every shared accepted-prefix state for each of
MTP off/2/3/4: 128/78/74/58 common boundaries and zero field mismatches. This is
correctness evidence, not eager-versus-captured performance; state tracing
synchronizes execution.

The 28-GiB supervisor passed with a six-GiB floor. Minimum host availability
was 14,458,286,080 bytes (13.47 GiB); minimum effective admission headroom was
11,199,172,608 bytes (10.43 GiB). OOM counters remained zero. Clock reads were
observational only; EMC access was denied and energy was not measured. Raw
per-service logs, trace results, memory samples and tegrastats are in
`trace/` and `supervisor/`. The command matched the captured run's command with
`eager` as the final argument; hashes are in `SHA256SUMS.txt`.

This extends correctness for the specific opt-in Q6 accepted-only policy,
prompt, output length, KV format, cache and context. It does not qualify the
default window-count adaptive path or other requests, and it does not promote
eager decoding.

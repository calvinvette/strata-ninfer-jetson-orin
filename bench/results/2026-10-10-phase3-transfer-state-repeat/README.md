# Same-mode transfer state diagnostic — Orin — 2026-10-10

The original same-mode requests used `--expert-cache auto` and therefore did not
hold expert residency constant. The `spec4`/MTP pair selected 7,050 and 7,108
slots. Identical tokens and MTP draft counts were accompanied by different
persistent-state fingerprints. The `spec2`/MTP-off pair selected 7,570 and
5,679 slots and also differed in state. These raw failures are not evidence of
intrinsic run-to-run drift: Strata's log says GPU-computed resident experts round
differently from CPU-computed nonresident experts.

The narrower `spec2`/MTP-off one-token auto-cache repeat selected 5,602 and
5,634 slots, had 345 and 346 cache hits, emitted the same token, and differed in
final GDN, tail, pooled, pooled-full and KV hashes. Its prefill GDN fingerprints
matched. The first differing 16-bit GDN fingerprint was ordinal 10; this is a
locator, not a correctness hash. A [`spec2` fixed-cache counterpart](../2026-10-10-phase3-transfer-state-repeat-spec2-tg1-fixed-cache/README.md)
selected 6,519 slots in both processes, had 369 hits in each, and matched
prefill and final state exactly. The 8K `spec4` fixed-cache mapped/pread screen
also matched every state field in all three pairs. Together these comparisons
indicate that unmatched cache residency confounded the original diagnostics;
they do not quantify a general cache-size causal effect.

A second auto-cache `spec4` diagnostic enabled per-GDN fingerprints: the first
of 36 block subhashes matched and the remaining 35 differed. These subhashes
retain only 16 bits. A legacy one-token commit control still differed, though
its first differing block moved to ordinal 21. This branch is retained as
diagnostic evidence only; it does not establish a compute-kernel defect.

Attempts to disable the token graph in the serving harness are retained in
`../2026-10-10-phase3-transfer-state-repeat-spec2-tg1-no-graph/` and
`../2026-10-10-phase3-transfer-state-repeat-spec2-tg1-no-graph-fixed/`. That flag
controls the separate `session_loop` token path, not the serving verifier graph.
The first attempt failed its setup gate; temporarily bypassing that gate reached
the verifier, which correctly rejected the missing profile hit table before a
request. Neither attempt generated model output, so neither is a parity result.

Use fixed expert residency for subsequent comparisons. Retain auto-sizing
failures with their actual slot counts rather than attributing their state
differences to transfer mode. All raw process logs and supervisor telemetry are
preserved; no models or build artifacts are included.

# Verifier GDN position bracket attempt — Orin — 2026-10-20

This attempted to sample layer-26 state at verifier positions 255, 383, 447,
479, 495, 503, 507 and 511 to bracket the recovery divergence. The existing
capture hook runs only on the single-token verifier route; prompt prefill does
not call it at those token positions. The raw output therefore contains only
the two position-511 records and no comparison for the requested earlier
positions. The run itself passed supervision, but this is an unsupported
measurement cell and provides no earlier-position state evidence.

The runner now parses the raw record stream and requires every requested
position to appear once for the initial request and once for recovery. Future
attempts using the verifier hook will fail explicitly when their requested
positions are not observable. The prefill-chunk trace is separately reported in
`../layer26-gdn-prefill-state-comparison/`.

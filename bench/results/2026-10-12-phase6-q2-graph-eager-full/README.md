# Phase 6 Q2_0 graph/eager extended screen

This Orin AGX campaign extends the three-pair graph/eager screen to longer
outputs, seven MTP-off pairs, and three MTP2 pairs. It uses the same Q2_0
native pack and explicit model paths as the earlier Phase 3–5 controls. The
candidate executable SHA256 is
`1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`.
All runs used a 28 GiB cgroup limit, preserved the six-GiB host headroom
floor, and left clocks under the platform's dynamic policy. EMC clock reads
were denied by the kernel; rail energy is raw tegrastats data and is not
process-attributed.

## Workloads and execution

`workloads.json` defines the 512-token prompt/64-token generation and
2048-token prompt/128-token generation cells. Each pair used one service per
route, same-day paired controls, and recorded output text and timings. The
MTP-off confirmation contains seven independent pairs; the MTP2 screen has
three. Warmups used the same two prompts with one generated token each.
Supervisor `pass` means the request completed within its resource guard; it
does not mean numerical qualification.

All three MTP2 pairs matched captured and eager outputs for both cells. Draft
and accepted counts were 36/27 at the short cell and 72/56 at the long cell
in every arm and pair. In the seven MTP-off pairs, all short-cell outputs
matched, but two of seven long-cell eager outputs differed from their paired
captured output. Both failures occurred when the short request preceded the
long request in the same eager service. The other five long-cell pairs
matched. Since numerical qualification failed, these timings are descriptive
only and do not qualify a performance change.

The descriptive paired medians showed no end-to-end basis for promotion. For
MTP-off, long-cell decode delta was 0.00%, request latency −0.10%, prompt
latency −0.26%, and TTFT +0.44%; short-cell decode was −5.05% and request
latency +5.55%. For MTP2, long-cell decode was −6.90% and request latency
+0.71%; short-cell decode was −1.79% and request latency −0.25%. These are
screening summaries only; they are not speedup claims.

## Request-order correctness follow-up

The MTP-off screen's order correlation prompted a traced API sequence using
the same 512- then 2048-token prompts. Both captured and eager services
completed the sequence under the same guard. The measured 128-token output
was byte-identical across routes (SHA256
`1c8cfd3f295a11767aff347608e30314cb6c1b9807f86cfcd9aee39deefe7a3f`). A
matched long-only API run produced the same output across routes, but its
output SHA256 was
`a868c12065a20f134dd5dbd9ec87132a8a471cb9743019ed60ca1292596e3376`.
Encoding both outputs with the retained tokenizer gives 128 tokens and their
first difference is token 56. This establishes a request-order effect in this
traced setup, shared by captured and eager routes; it is not evidence of an
eager-only defect.

The first long request in the sequence matches the long-only prompt-end
fingerprint. After the intervening 64-token short request, the second long
request has the same prompt tokens and ending input token, and its prompt-end
fingerprint changes from GDN `cc1f42c906e4e844`, KV
`96fc7df6042402e8`, pooled `934782f203425207` to GDN
`ed8853a3a5f3bd61`, KV `0b022d3b9e533de0`, pooled
`bb067be8bff2666d`. The PLE `9a523bcb9cc222d0` and tail
`4bffd99767bd2352` hashes remain equal. Captured and eager second-request
fingerprints match each other. The trace narrows the discrepancy to state
outside those matching PLE/tail fields, but does not yet identify its cause.

This is an unresolved shared-runtime request-order correctness failure. Do
not promote eager decode or interpret the paired timing deltas as qualified
until a minimal same-service reproduction is understood and the accepted
prefix state is checked against an independent reference.

The follow-up under `minimal-sequence-captured/` and
`minimal-sequence-eager/` used the API harness's built-in full-length warmup
(short, then long) followed by the measured short/long sequence. It therefore
does not remove warmups. The captured and eager arms matched exactly at each
request. In each arm the first long response hash was
`4035b29278c046f4776864fe71c4ffc02c64aecbaf8b1ed2122168240eaba202`, while
the second was
`753ec32d031de32765bae05d48b773c34103c45616d04807faf1b5c36651e5c2`.
The short outputs were identical in both arms and both iterations. The initial
`--spec 0` attempt failed startup because the native pack requires `--spec 2`;
that failed artifact is retained alongside the corrected runs. This follow-up
confirms a repeated-workload effect in the shared service path, but the
intervening long request means it is not yet a minimal short-to-long
reproduction. A custom single-pass API client should next issue only one short
request followed by one long request in a fresh service, then compare with a
fresh long-only service and inspect the first divergent accepted-prefix state.
Preserve both serving routes and the supported MTP2 configuration.

## Retained evidence

- `mtp-off/`, `mtp-off-confirm/`, and `mtp2/` contain raw paired campaigns,
  per-arm request output, workload order, supervisor memory and clock samples.
- `sequence-captured/` and `sequence-eager/` contain matched request-order
  traces, API responses, engine logs, and supervisor records.
- `api-traced-captured-retry/` and `api-traced-eager/` contain long-only
  comparison runs. The failed initial adapter invocation is retained in
  `api-traced-captured/` with its failure artifacts.
- Tokenizer and model inputs remain in `~/models/`; no model files are copied
  into this result directory.

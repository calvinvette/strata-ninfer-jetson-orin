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

This is unresolved output sensitivity in the shared runtime. Do not promote
eager decode or interpret paired timing deltas as qualified without an
independent output-quality budget.

## Independent quality screen

This screen compares the same deterministic computer-information prompt
with default adaptive swaps and `--adapt-swaps 0`. The prompt is built on the
retained `pp2048-tg128` token fixture (`tokens_sha256`
`6989a4393a67b2aec9bbf7073ed97b13f9c5d16d78c9b305b77c73a6028d4db5`); after
chat formatting the API reports 2,094 prompt tokens. Its rubric requires at
least 200 words, the exact `Processor:` prefix and `17 x 19 = 323` statement,
and mentions of fetch, decode, execute, RAM, binary, input and output.
Temperature is zero. Each fresh service receives one request; adaptive and
no-swaps runs are sequential, under a 28 GiB cgroup with the six-GiB host floor.
No clocks are changed and energy is not attributed.

The initial 256-token pair produced identical 205-word replies (SHA256
`81043c22955fe9b7fe912cdd6c436c6c87575e08babcae60bb67e518ecea6f9d`) with
the required prefix, arithmetic and six of seven topic terms. Both stopped at
the length limit before mentioning output, so this pair is retained as an
incomplete rubric result. The matched 512-token-cap pair finished naturally
after 304 adaptive and 306 no-swaps tokens. Both passed the full checklist and
were over 200 words (245 and 247 by whitespace-separated word count). Their
reply hashes were respectively
`64053be6f7507139c24fba69372796113bf3e4dcb90fa37de2cbeba245279dd8` and
`97912693cfc2677df85c1581f9fdd5793e66be45a494666c40942e0585244caf`; the
small wording difference is in the output-device explanation. Both supervisor
runs passed with minimum available memory of 18.00 and 17.96 GiB. API elapsed
times were 116.0 s and 164.6 s, respectively; a single unrandomized pair is
not timing evidence.

This is a narrow task-level screen, not a general language-quality evaluation
or a demonstrated quality budget for expert residency changes. It shows that
both settings can satisfy this one task; it does not classify the previously
observed output changes as acceptable for broader workloads. No configuration
is promoted and Phase 6 remains open. Raw API outputs, configs and supervisor
telemetry are retained in `quality-adaptive*/` and `quality-no-swaps*/`; the
512-token workload definition SHA256 is
`e43741901e121b6bdf36c58f8ed8698bd63b6475806f2d3e16d486c50cf9a340`.

The API harness's built-in warmup is a full-length request, so the follow-up
under `minimal-sequence-captured/` and `minimal-sequence-eager/` first showed
that each route repeated the same changed long output after a short/long
warmup. To remove that extra history, `minimal_api_driver.py` then sent only
one 512/64 request followed by one 2048/128 request to a fresh service, with
temperature 0 with MTP disabled (`--spec 2` is still required by the native
pack). A separate fresh captured service received
only the long request. Both direct sequence runs completed under the 28 GiB
cap and six-GiB host floor; minimum available host RAM was 18.1 GiB. The
captured and eager sequence outputs matched each other exactly. Their long
response SHA256 was
`4035b29278c046f4776864fe71c4ffc02c64aecbaf8b1ed2122168240eaba202`, while
the fresh long-only response SHA256 was
`a868c12065a20f134dd5dbd9ec87132a8a471cb9743019ed60ca1292596e3376`. Both
responses contain 128 tokenizer IDs; the first token difference is at index
8. The short output was byte-identical across routes. This establishes output
sensitivity to expert-residency history in the tested binary and configuration;
captured/eager mode alone does not explain it.

An ablation localized the sensitivity to adaptive swaps. With default swaps,
the fresh long-only captured output was `a868c120…` and the short→long output
was `4035b292…`. With `--adapt-swaps 0`, captured and eager short→long runs
and the captured long-only control all produced `863e819f…`. Keeping swap
tracking enabled but setting `--adapt-every 100000` produced that same
`863e819f…` output for both the short→long sequence and the long-only control.
Thus the observed text change follows performing adaptive residency swaps,
not merely allocating or updating usage counters, and it reproduces across
both decode routes when swaps are disabled. This does not prove that swapped
expert weights are wrong: the runtime can compute a resident expert on GPU and
a nonresident expert on CPU, and those paths may round differently. The source
documents this sensitivity around adaptive swap timing. We need an independent
quality budget before classifying the output shift as unacceptable or accepting
the optimization.

The accepted-prefix trace adds an important limit: with state-hash tracing
enabled, the same direct short→long sequence produced the long-only output
hash (`a868c120…`). Its prompt-end GDN/KV/pooled hashes still differed from the
long-only traced run (`dd5f620e…` versus `cc1f42c9…` for GDN; `b4314dca…`
versus `96fc7df6…` for KV). PLE and tail hashes matched. Because instrumentation
changes the output of the failing no-trace case, these state logs are
perturbative and cannot identify the production divergence. Keep correctness
qualification on uninstrumented output/state checks until a non-perturbing
accepted-prefix observation is available.

The initial `--spec 0` attempt failed startup because the native pack requires
`--spec 2`; that artifact remains with the corrected runs. State hashing also
changes the sequence output, so the next step is an independent quality check
and a non-perturbing observation of the expert-residency path.

## Retained evidence

- `mtp-off/`, `mtp-off-confirm/`, and `mtp2/` contain raw paired campaigns,
  per-arm request output, workload order, supervisor memory and clock samples.
- `sequence-captured/` and `sequence-eager/` contain matched request-order
  traces, API responses, engine logs, and supervisor records.
- `manual-sequence-*` and `manual-long-captured/` retain direct one-pass API
  requests without the benchmark harness's automatic warmup. The driver is
  `minimal_api_driver.py`.
- `manual-traced-sequence-captured/` and `manual-traced-long-captured/` retain
  accepted-prefix state hashes. The trace changes the output of the sequence
  case, so it is explicitly treated as intrusive diagnostic evidence.
- `noadapt-*` and `adapt-delayed-*` retain swap ablations and matched controls.
- `trace-adapt-sequence-captured/` retains the opt-in trace attempt; the
  serving path emitted no per-round trace lines.
- `api-traced-captured-retry/` and `api-traced-eager/` contain long-only
  comparison runs. The failed initial adapter invocation is retained in
  `api-traced-captured/` with its failure artifacts.
- Tokenizer and model inputs remain in `~/models/`; no model files are copied
  into this result directory.

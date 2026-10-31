# Q2_0 NInfer backend screen with adaptive 5K residency

Date: 2026-10-31. Device: Jetson AGX Orin (`orin1`), aarch64, SM87, CUDA
12.6. This three-pair, same-day screen asks whether NInfer gains an end-to-end
advantage when adaptive cache swaps expose more resident expert work. The
primary metric was decode throughput; the preregistered useful-effect screen
was at least 5% median improvement, with a paired 95% interval excluding zero
and no more than 5% regression in prompt throughput or TTFT.

## Controls and inputs

Each independent process served one warmup and one measured request using the
same held-out `NIMBUS-7319` exact-value retrieval prompt (512 input, 128 output
tokens). Pair order was Strata→NInfer, NInfer→Strata, Strata→NInfer. The only
backend change was `--expert-backend strata` versus strict NInfer. Both arms
used the same Q2_0 model, PLE pack, 5,000-slot starting expert profile, 8K
configured context, prefill chunk 128, speculation window 2 with draft
generation disabled, eight workers, adaptive swaps every four windows (up to
96 exchanges), no prompt cache, no PCIe staging, 6 GiB resident budget, a
separate 3 GiB workspace reserve and 9 GiB host reserve. Timing runs had
tracing disabled. The six measured responses all returned the exact
`NIMBUS-7319` prefix, 128 tokens and the same complete response hash.

The control and candidate both began with the same profile-ranked 5,000 slots.
After the warmup, engine counters showed the same 76.0% GPU-cache hit rate
(46,694/61,440 lookups) and 1,142 adaptive exchanges for each backend. This
matches the amount of resident work observed, but the dynamic slot map was not
independently hashed; the comparison is a backend screen under the same cache
policy, not a strict route-replay operator ablation.

Before this screen, a single paired pilot used the same 5,000-slot profile
with adaptation disabled. It passed the exact answer checks but achieved only
21.4% NIMBUS and 21.3% ORBIT GPU hits. That static profile did not provide the
intended high-hit condition, so no performance conclusion was drawn from its
single pair. The adaptive condition is the relevant result below.

The measured source code is from `e781e411`; executable SHA256 is
`fd67288c399d895be036dab344e30caab3d081540bfc552f22dac6a5fc33644a`. The Q2_0
GGUF shards are the same verified files as the [4K-cache backend screen](../2026-10-31-e6-q2-ninfer-backend-4k-tg128-screen/README.md):
`69820c02…b199b720` and `316b46f3…161e113`. The profile SHA256 is
`b3e62120…7e85fb8c`. Model, profile and PLE files remain under `~/models/`.
The exact non-prompt experiment settings and randomized order are in
[`campaign.json`](campaign.json).

## Results

Positive effects mean NInfer is faster or has lower latency. Intervals are
bootstrap 95% intervals over the three independent paired process blocks;
these are screening estimates.

| Metric | Strata median | NInfer median | NInfer paired effect | Paired 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Prompt throughput | 22.8 tok/s | 22.8 tok/s | 0.00% | −6.50% to 0.00% |
| Decode throughput | 9.3 tok/s | 9.2 tok/s | −1.08% | −5.21% to 0.00% |
| First-visible TTFT | 22.65 s | 22.70 s | −0.23% | −6.65% to +0.33% |
| Client total | 36.24 s | 36.45 s | −0.30% | −6.01% to −0.14% |

The NInfer decode median was 1.08% lower, and no metric reached the 5%
improvement screen. One pair favored Strata by about 5%; the two other pairs
were close to tied. The response hash and measured hit counters matched in all
three pairs. This does not support a seven-pair confirmation: the screen gives
no positive performance hypothesis to confirm. The earlier 4K-cache backend
screen and this 5K adaptive screen both fail to show an NInfer-specific
end-to-end gain, even though the latter reached 76% GPU hits after warmup.

The three-request p95 values are descriptive only: 36.42 s for Strata and
36.54 s for NInfer. Samples are too few for a serving-tail claim. The complete
per-pair sanitized data and bootstrap calculation are in
[`paired-summary.json`](paired-summary.json); raw prompts, responses and
telemetry remain under `/tmp/e6-ninfer-adapt-5k/`.

## Resources and limits

All six measured processes passed the supervisor and exact-output checks. The
minimum sampled available RAM was 8.98 GiB, above the preserved 6 GiB floor;
peak sampled swap was 2.42 GiB and sampled cgroup OOM-kill counters were zero.
The 6 GiB expert RAM complement, 5,000 GPU slots and separate 3 GiB workspace
reserve were retained. CPU clocks ranged 729.6–2,201.6 MHz and GPU clocks
306–1,300.5 MHz; EMC readback was unavailable and clocks were not controlled.
Energy was not measured.

This is one 512+128 synthetic retrieval workload, three pairs, one configured
context and one cache size. Matching text and answer prefix do not establish
general task quality, long-context parity or exact persistent-state equality.
The 5K adaptive profile is not recommended as a default. E6 remains open for
its wider quality and workload gates; E7 still proposes no NInfer release
profile.

## Correctness-only persistent-state check

One additional Strata/NInfer pair repeated the warmup and measured request
with final-state hashing enabled. The two backends matched each of the ten
recorded persistent-state fields at both request ordinals, and their response
hashes matched by ordinal. Within each backend, however, the warmup and
measured final states differed in GDN, PLE, tail, pooled, KV, pooled-full and
previous-embedding fields; the response hashes also differed by request
ordinal. Thus this pair shows cross-backend state agreement alongside a
shared request-order change. It does not establish repeatability across
requests or identify the source of the change. Minimum available host memory
was 8.95 GiB for Strata and 9.02 GiB for NInfer. Hashing timings are excluded.
See [`state-parity.json`](state-parity.json).

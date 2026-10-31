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

## Corrected reset and prefill-boundary capture

The first attempt at this capture omitted reset and prompt-boundary hashes
because the API harness did not set those environment switches from its CLI
flags. That attempt is excluded from reset-state conclusions. The harness now
sets the opt-in variables and its focused tests pass. In a corrected pair, the
post-reset state and sampled prefill checkpoints at positions 128, 256 and 384
matched between the warmup and measured requests. At the prompt boundary
(position 511), GDN, pooled, KV and pooled-full fingerprints differed; PLE,
tail and other recorded fields matched. Strata and NInfer still matched at
every checkpoint by request ordinal. The engine reported 684 adaptive expert
exchanges after warmup and 1,142 after the measured request. This localizes the
first **recorded** within-process difference to the final prefill segment,
after the adaptive cache had changed. At the time this capture was made, it did
not identify the exact slot or prove that migration caused the state change;
the later owner-map diagnostic below resolves the first limitation, not the
causal question. See
[`boundary-capture.json`](boundary-capture.json); state-hash timings are not
performance measurements.

Follow-up per-layer prefill traces found that recurrent-state fingerprints at
GDN layers 5, 13, 16 and 18 match across the two request ordinals at every
sampled chunk. Layer 15 was rejected because it is QSA, not GDN. These selected
layers do not explain the changed aggregate GDN hash; the other GDN layers and
aggregate components remain to be checked. Raw layer snapshots stay under
`/tmp/e6-ninfer-adapt-5k/` and their hashes are recorded in the boundary JSON.

## Adaptive residency map capture

A follow-up captured `STRATA_RESIDENCY_DUMP` at startup and saved the learned
profile at process exit for one-request and two-request runs. The startup dump
matched the original Q2_0 profile's first 5,000 experts exactly in both
backends. Reloading Strata's saved post-warmup profile reproduced its first
5,000 IDs in the independently dumped startup map with zero symmetric
difference. This validates use of the saved profile's first 5,000 entries as
the resident owner set for these runs.

| Checkpoint | Strata profile SHA-256 | NInfer profile SHA-256 | Resident-map comparison |
| --- | --- | --- | --- |
| After warmup request | `29588fb2714f7ee4e7c4e23522c3b398c177b37def922ab32ffe45fad90ea010` | `29588fb2714f7ee4e7c4e23522c3b398c177b37def922ab32ffe45fad90ea010` | Entire profile identical; 0 resident-ID symmetric difference |
| After measured request | `71cf28d385d6ccf22c122830d22e62451811ffaf30296414ec8207c1939c83ef` | `71cf28d385d6ccf22c122830d22e62451811ffaf30296414ec8207c1939c83ef` | Entire profile identical; 0 resident-ID symmetric difference |

The warmup and measured response hashes also match across backends and match
the earlier captures (`576272a200f58b5b0a72f489ac1a2019098ec2939ac1480a2531f90a8e337cd2`
and `1719e86b58f64cf00c23749b67feacac453c76684a351ca0480d026111124e77`).
Each backend replaced 2,909 of its initial resident IDs by the end of warmup,
then replaced 952 more between warmup and the measured request (1,904 IDs in
the latter symmetric difference). The log's `exchanged with the VRAM tier`
counter is narrower: `FileExpertSource::commit_exchanges()` increments it for
committed RAM-complement ownership rotations. It is not a count of all changes
in the GPU resident map and must not be used as that proxy. The captured map
does not explain the prefill-state divergence or establish it as a cause.

The NInfer two-request diagnostic passed under the 6 GiB admission floor; its
minimum sampled available host RAM was 9.04 GiB. This was a state/map capture,
not a performance measurement. The profile binaries and raw residency dumps
remain under `/tmp/e6-ninfer-adapt-5k/maps/` and are not committed.

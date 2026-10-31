# Q2_0 fixed-map and backend comparison on held-out tasks

Date: 2026-10-31. Hardware: Jetson AGX Orin, CUDA backend. This experiment
measured a held-out prompt, not a representative workload suite.

## Result

The fixed learned resident map produced a large, repeatable decode improvement
under **both** Strata and strict NInfer. In seven confirmation pairs, decode
throughput increased 127.9% under NInfer (4.53 to 10.50 tok/s; paired bootstrap
95% interval +121.5% to +134.6%) and 130.1% under Strata (4.50 to 10.36 tok/s;
+118.4% to +132.7%). The learned map raised measured GPU expert-cache hits from
21.4% to 74.1%. Outputs were identical within every pair. This isolates
resident-map selection and cache hits as the source of the large observed gain;
it does **not** show a comparable NInfer-kernel gain.

With the exact resident map held fixed, the three-pair NInfer-versus-Strata
screen showed +0.7% decode TPS on the original map (4.44 vs 4.48 tok/s; interval
−1.2% to +8.0%) and −2.2% on the learned map (10.41 vs 10.31 tok/s; −4.9% to
+2.9%). Neither median met the 5% useful-effect gate, so these cells were not
confirmed. The small samples leave uncertainty, particularly on the original
map, but give no evidence of a useful end-to-end NInfer advantage in this
workload.

## Paired map results

Changes are learned-map versus original-map. Latency changes below are negative
when faster. Intervals are percentile bootstrap intervals over paired process
blocks; the three-pair screens are exploratory and the seven-pair cells are
confirmations for this one prompt and shape.

| Backend and stage | Original median | Learned median | Paired change (95% interval) |
| --- | ---: | ---: | ---: |
| NInfer decode | 4.53 tok/s | 10.50 tok/s | +127.9% (+121.5%, +134.6%) |
| NInfer prompt processing | 19.69 tok/s | 27.33 tok/s | +28.7% (+17.0%, +38.8%) |
| NInfer first visible token | 26.24 s | 18.90 s | −22.3% (−28.0%, −14.9%) |
| NInfer client request time | 40.14 s | 24.91 s | −34.8% (−37.9%, −29.1%) |
| Strata decode | 4.50 tok/s | 10.36 tok/s | +130.1% (+118.4%, +132.7%) |
| Strata prompt processing | 19.37 tok/s | 22.84 tok/s | +18.3% (+16.3%, +42.1%) |
| Strata first visible token | 26.68 s | 22.61 s | −15.5% (−29.6%, −14.1%) |
| Strata client request time | 40.69 s | 28.59 s | −29.9% (−38.3%, −28.8%) |

The three-pair screens showed the same direction: NInfer decode +134.2% and
Strata +136.9%. Their wide or discrete bootstrap intervals are screening
estimates only. The seven-pair confirmations are reported above.

## Same-map backend screens

Strata is the baseline and strict NInfer is the candidate. Both maps gave
identical hit rates between backends and the same exact response SHA-256
(`57a97d72bfaf479c632c86cc353fbf29f5073274b2d58cc293939d3c4b3139cc`) in all
three pairs.

| Fixed map | Metric | Strata median | NInfer median | NInfer paired change (95% interval) |
| --- | --- | ---: | ---: | ---: |
| Original | Decode | 4.44 tok/s | 4.48 tok/s | +0.7% (−1.2%, +8.0%) |
| Original | Prompt processing | 19.42 tok/s | 19.59 tok/s | +1.1% (+0.9%, +11.7%) |
| Original | First visible token | 26.59 s | 26.40 s | −1.1% (−9.6%, −0.7%) |
| Learned | Decode | 10.41 tok/s | 10.31 tok/s | −2.2% (−4.9%, +2.9%) |
| Learned | Prompt processing | 28.23 tok/s | 28.28 tok/s | −2.2% (−20.5%, +27.1%) |
| Learned | First visible token | 18.29 s | 18.30 s | +2.3% (−21.2%, +25.7%) |

These are three-pair screens. The decode medians are below the 5% threshold;
there was no confirmation campaign. The intervals are coarse and do not prove
that backend effects are exactly zero.

## 2K prompt replication

A separate 2,048-token retrieval/arithmetic fixture placed markers at 10%, 50%
and 90% of the prompt and asked for their exact codes and numeric suffix sum.
The response stopped naturally at 47 tokens and matched the complete expected
string in every measured arm. Three randomized screen pairs followed by seven
confirmation pairs used the same fixed maps, strict NInfer, context capacity
8,192 and other launch controls as above.

| Metric | Original map median | Learned map median | Paired change (95% interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 5.07 tok/s | 7.70 tok/s | +52.0% (+50.9%, +58.4%) |
| Prompt throughput | 31.78 tok/s | 42.15 tok/s | +32.3% (+30.5%, +43.4%) |
| First visible token | 64.73 s | 48.79 s | −24.4% (−30.2%, −23.4%) |
| Client request time | 73.72 s | 54.79 s | −25.6% (−31.3%, −24.7%) |

GPU expert-cache hits increased from 21.1% to 47.7%. Minimum request-window
available RAM was 9.15 GiB, sampled cgroup OOM-kill counters remained zero,
and the six-GiB floor was maintained. One original-map NIMBUS warmup took
127.6 s; its measured 2K request was within the campaign range (31.7 prompt
tok/s and 5.1 decode tok/s), so the block was retained. Energy was not
measured; EMC readback was unsupported as noted above. This confirms a
residency-map effect for one 2K prompt. It does not compare NInfer and Strata
kernels at 2K.

## Controls and identity

- Model: Qwen3.8-Flash-Next GSQ-RCO Q2_0, two GGUF shards. SHA-256 values:
  `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720` and
  `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
- Source revision: `29a26c8f702cd06fcc4a12812f10fe8225d2f8ca`; executable SHA-256:
  `fd67288c399d895be036dab344e30caab3d081540bfc552f22dac6a5fc33644a`.
- Both maps have 5,000 GPU-resident slots. They overlap in 2,091 slots and
  differ by 2,909 replacements. Both use the same ordered 4,660-entry RAM
  complement, sized to the 6 GiB resident budget. The original and learned
  profile SHA-256 values are `781fbe88884fbd263736bd4812c9abddfa59c707e2b2c1acad6cd40f6182cd64`
  and `76a1644f56d985fdd54a5816aadd39ce9356190dbaa828a293fab8462f507087`.
  The shared RAM-complement SHA-256 is
  `3d7519b9d41ef7bd6462b0cc800408fc4d708d922a5d0968f3dcbaf75f5954f5`.
- Fixed context capacity: 8,192; measured prompt/output: 512/64 tokens;
  prompt cache, PCIe staging and adaptive swaps disabled; eight pool workers;
  3 GiB workspace reserve; fp16 KV. Strict mode was enabled for NInfer.
- Every process received the same 512-token NIMBUS warmup, then one held-out
  ORBIT exact-retrieval request. The measured completion was exactly 64 tokens,
  began with `ORBIT-4826`, and matched its paired response byte-for-byte.
  Three randomized screen pairs and seven randomized confirmation pairs were
  run per backend for the ORBIT map effect. Separate three-pair screens compared
  backends on each fixed map. All 26 ORBIT/map and same-map backend pair blocks
  (52 processes) passed the supervisor and workload checks.
- Every process retained the six-GiB physical-memory admission floor. Minimum
  request-window available RAM across the campaigns was 9.15 GiB; peak observed
  swap use was 2.61 GiB. Sampled cgroup OOM-kill counters stayed zero. Observed
  dynamic CPU frequencies ranged 730–2,202 MHz and GPU frequencies 306–1,301
  MHz. EMC frequency readback was unsupported because the debugfs rate file
  denied access. Clocks were not changed. Energy was not measured; saved
  tegrastats rail samples do not establish whole-board energy.

## Limits and interpretation

The learned profile was trained from prior Q2_0 routing observations, then
measured on two separate exact-lookup prompts with adaptation disabled. The
second prompt changed the catalog subject and answer to alpine seed samples
and `MAPLE-6159`; it was verified as exactly 512 prompt tokens with Strata's
tokenizer. Across three screen pairs and seven confirmation pairs, learned-map
decode improved 114.5% in the screen and 113.5% in confirmation (4.80 to 10.25
tok/s; paired bootstrap 95% interval +109.8% to +117.3%). Prompt throughput
improved 18.0%, first visible token latency fell 15.3%, and client request time
fell 27.9%. GPU hit rate increased from 22.1% to 73.8%. All 20 processes passed
the exact `MAPLE-6159` prefix check. Full explanatory text differed between
maps, so this does not claim text equivalence or semantic grading.

The evidence covers two held-out 512-token exact lookups and one 2,048-token
retrieval/arithmetic prompt. The short tasks are in the same synthetic lookup
family; the long fixture tests exact multi-position retrieval and arithmetic.
This is still one model and narrow task coverage, not broad quality
qualification. These results do not qualify other prompt lengths, models,
memory budgets, or sustained service loads.

The primary finding is that a fixed 5K residency map with more useful experts
in GPU memory more than doubled decode speed on the two 512-token exact-lookup
prompts and improved decode 52.0% on the 2K retrieval prompt, under NInfer; the
512-token ORBIT map effect was also confirmed under Strata.
The same-map screens did not show a 5% NInfer end-to-end gain. Continue the
planned context/workload matrix and broader quality/state gates before changing
release defaults or claiming NInfer acceleration.

Pair-level values, response hashes and memory/clock summaries are in
[`evidence.json`](evidence.json). Raw process captures remain under
`/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/` and are not committed.

# Q2_0 fixed-map and backend comparison on held-out tasks

Date: 2026-10-31 to 2026-11-02. Hardware: Jetson AGX Orin, CUDA backend. This experiment
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

With the exact resident map held fixed, same-map NInfer-versus-Strata screens
showed decode changes of +0.7% on the original 512-token map, −2.2% on the
learned 512-token map, +4.2% at 2K, 0.0% at 4K, 0.0% at 8K, 0.0% at 16K and −1.4% at 32K. None met the 5% useful-effect
gate, so these cells were not confirmed. The three-pair intervals are coarse;
the 4K screen also had one NInfer prefill outlier. These screens give no
evidence of a useful end-to-end NInfer advantage at these tested settings, but
do not establish equivalence.

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

With the learned map fixed, a separate three-pair 2K screen directly compared
Strata and strict NInfer on the same 2,048-token retrieval/arithmetic request.
All answers matched the exact four-field string, and both backends had 47.7%
expert-cache hits.

| Metric | Strata median | NInfer median | NInfer paired change (95% interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 7.66 tok/s | 7.69 tok/s | +4.2% (−3.9%, +5.0%) |
| Prompt throughput | 41.97 tok/s | 42.67 tok/s | +1.7% (−10.9%, +14.3%) |
| First visible token | 49.00 s | 48.20 s | −1.6% (−12.3%, +12.2%) |
| Client request time | 55.18 s | 54.12 s | −1.9% (−11.6%, +11.2%) |

The decode median remained below the 5% useful-effect threshold, so this
screen was not confirmed. Minimum request-window available RAM was 9.17 GiB,
with zero sampled cgroup OOM kills. This gives no evidence of a useful NInfer
kernel advantage at 2K either, although the three-pair interval remains coarse.

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

## 4K prompt confirmation

A third tokenizer-verified retrieval/arithmetic fixture placed exact lookup
codes at 10%, 50% and 90% of a 4,096-token prompt. It requested the three
codes and their numeric suffix sum. The learned-map intervention was screened
in three pairs first, then confirmed in seven independent-process pairs with
strict NInfer, the same 5K resident maps, identical ordered 4,660-entry RAM
complements, and adaptation disabled. Every measured response contained the
complete expected four-field string and stopped naturally after 47 tokens.

| Metric | Original map median | Learned map median | Paired change (95% interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 5.1 tok/s | 7.8 tok/s | +54.0% (+47.2%, +58.0%) |
| Prompt throughput | 44.7 tok/s | 58.9 tok/s | +30.0% (+28.3%, +36.4%) |
| First visible token | 91.79 s | 69.69 s | −23.1% (−26.6%, −22.1%) |
| Client request time | 100.67 s | 75.51 s | −24.0% (−27.5%, −23.0%) |

GPU expert-cache hits rose from 21.5% to 48.2%. Minimum available RAM during
the measured request windows was 9.16 GiB, above the six-GiB admission floor;
sampled cgroup OOM-kill counts stayed at zero. CPU and GPU frequencies were
observed dynamically (729.6–2,201.6 MHz CPU; 306–1,300.5 MHz GPU), with no
clock changes. EMC readback was denied and energy was not measured. This
confirms a residency-map performance effect for one 4K synthetic retrieval
prompt; it does not establish broad semantic quality or a general NInfer-kernel
advantage. Pair-level data and hashes are in `evidence.json`; raw captures are
under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task4096-confirmation/`.

### Same-map backend screen at 4K

A three-pair screen then compared Strata and strict NInfer on the same learned
5K map, with adaptation off. All six measured requests returned the identical
47-token expected answer and both backends had the same 48.2% expert-hit rate.

| Metric | Strata median | NInfer median | NInfer paired change (95% interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 8.0 tok/s | 7.8 tok/s | 0.0% (−3.8%, +1.3%) |
| Prompt throughput | 60.7 tok/s | 58.4 tok/s | −3.8% (−30.1%, +1.4%) |
| First visible token | 67.66 s | 70.28 s | +3.9% (−1.3%, +42.9%) |
| Client request time | 73.34 s | 76.19 s | +3.9% (−1.4%, +39.6%) |

The decode median did not meet the 5% gate, so no confirmation was run. One
NInfer pair had substantially slower prefill (41.2 tok/s versus 58.9 tok/s for
its Strata control), producing the wide three-pair prompt and latency
intervals. Minimum available RAM was 9.19 GiB; sampled OOM-kill counts were
zero and clocks remained dynamic. This screen gives no evidence of a useful
NInfer backend gain at 4K, but its small sample does not establish equivalence.
Pair-level data is in `evidence.json`; raw captures are under
`/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task4096-backend-screen/`.

## 8K prompt replication

An 8,192-token version of the three-position retrieval/arithmetic fixture was
run at a 16,384-token configured context, retaining the same two fixed maps,
strict NInfer backend, 5K resident slots and ordered 6-GiB RAM complement.
Three screening pairs followed by seven confirmation pairs were measured. All
20 measured requests returned the exact full answer at 8,192 prompt tokens and
47 naturally stopped output tokens.

| Metric | Original map median | Learned map median | Paired change (95% interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 5.1 tok/s | 7.6 tok/s | +49.0% (+46.2%, +53.8%) |
| Prompt throughput | 60.7 tok/s | 73.3 tok/s | +17.8% (+14.4%, +27.4%) |
| First visible token | 135.19 s | 111.91 s | −15.2% (−21.6%, −12.6%) |
| Client request time | 144.15 s | 117.97 s | −15.5% (−22.4%, −13.9%) |

GPU expert-cache hits increased from 21.3% to 47.4%. Across screen and
confirmation request windows, minimum available RAM was 8.99 GiB, above the
six-GiB admission floor; sampled cgroup OOM-kill counts stayed at zero. CPU
and GPU frequencies were observed dynamically, EMC readback was denied, and
energy was not measured. This confirms a fixed-residency effect for one
synthetic 8K retrieval task under NInfer. It does not qualify broad task quality
or establish a backend advantage; the next step should use another prompt
family and then test larger actual input lengths. Pair-level data are in
`evidence.json`, with raw captures under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task8192-{screen,confirmation}/`.

## 16K prompt replication

A tokenizer-verified 16,384-token retrieval/arithmetic fixture has passed a
three-pair screen at 32,768 configured context. All six measured cells returned
the exact answer with 47 output tokens. Under strict NInfer, the learned map
improved decode +46.9% (4.9 to 7.2 tok/s; three-pair bootstrap interval +44.0%
to +51.0%), prompt throughput +4.5%, and client time −5.4%; expert hits rose
21.3% to 48.2%. Minimum available RAM was 8.57 GiB, above the six-GiB floor,
with zero sampled OOM kills. This cleared the 5% decode screen gate. Seven
randomized confirmation pairs then showed a +49.0% decode change (4.9 to 7.3
tok/s; paired 95% interval +43.1% to +51.0%), +14.7% prompt throughput,
−13.0% first-visible latency and −13.8% client time. Confirmation outputs
also matched exactly in all fourteen cells. Minimum available RAM across
screen and confirmation was 8.57 GiB, with peak observed swap use of 5.10 GiB
and no sampled OOM kills. Clock controls were untouched, EMC readback was
denied and energy was not measured. This confirms a fixed-map effect for one
synthetic 16K retrieval task under NInfer, not broad quality or long-context
generalization. Pair-level evidence is in `evidence.json`; raw captures are
under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task16384-{screen,confirmation}/`.

## 32K prompt screen

A tokenizer-verified 32,768-token retrieval/arithmetic fixture was screened at
65,536 configured context using the same strict-NInfer controls and fixed 5K
maps. All six measured requests returned the exact expected answer in 47
tokens. The learned map's decode median was 6.9 versus 4.7 tok/s for the
original map, a +43.8% paired median, but the three-pair bootstrap 95% interval
was −30.4% to +46.8%. One learned-map cell decoded at 3.2 tok/s (its paired
baseline was 4.6); the other two learned-map cells were 6.9 tok/s. The screen
therefore failed the pre-set confirmation gate and no confirmation was run.
Do not interpret the median alone as a 32K performance confirmation.

Prompt throughput changed +4.5% (96.3 to 100.6 tok/s), first-visible latency
fell 4.4% (341.1 to 326.2 s), client time fell 5.0% (350.4 to 332.6 s), and
GPU hits increased from 21.6% to 48.2%. Minimum available RAM was 7.77 GiB,
peak observed swap use was 5.26 GiB, and sampled OOM-kill counts stayed zero.
The GPU clock range was 306–1,300.5 MHz; CPU clocks ranged 729.6–2,201.6 MHz.
The slower learned-map cell coincided with lower CPU frequency during its
decode window while GPU frequency remained at 1,300.5 MHz; this observation
does not establish a cause. Clocks were not controlled, EMC readback was
denied, and energy was not measured. This is one synthetic 32K task screen,
not a confirmed map effect, broad quality result, or general context claim.
Pair-level evidence is recorded in `evidence.json`; raw captures remain under
`/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task32768-screen/`.

## 64K prompt screen

A tokenizer-verified 65,536-token retrieval/arithmetic fixture was screened at
131,072 configured context using strict NInfer, the same 5K GPU maps and shared
6-GiB RAM complement. All six requests returned the full exact answer in 47
tokens. The learned map improved decode by +40.0% (6.3 versus 4.5 tok/s;
three-pair paired bootstrap 95% interval +34.8% to +40.0%). Prompt throughput
increased 3.4% (104.2 to 107.8 tok/s), first-visible latency fell 3.3% (629.8
to 608.5 s), client time fell 3.7% (639.5 to 615.5 s), and GPU hits rose from
21.5% to 48.4%. The decode effect clears the pre-set 5% median and interval
gate, so it qualifies for a separate seven-pair confirmation.

Minimum available RAM was 7.27 GiB, maximum observed swap use was 5.15 GiB,
and sampled cgroup OOM-kill counts were zero. CPU frequency ranged 729.6–2,201.6
MHz and GPU frequency 306–1,300.5 MHz; clocks were not controlled. EMC readback
was denied and energy was not measured. This is a screen for one synthetic
64K task, not confirmation, broad quality evidence or general long-context
qualification. Pair data are in `evidence.json`; raw captures remain under
`/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task65536-screen/`.

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

The evidence covers two held-out 512-token exact lookups and 2,048-, 4,096-,
8,192- and 16,384-token retrieval/arithmetic prompts. The short tasks are in
the same synthetic lookup family; the longer fixtures test exact
multi-position retrieval and arithmetic. The 8K and 16K measurements used
16K and 32K configured contexts respectively.
This is still one model and narrow task coverage, not broad quality
qualification. These results do not qualify other prompt lengths, models,
memory budgets, or sustained service loads.

The primary finding is that a fixed 5K residency map with more useful experts
in GPU memory more than doubled decode speed on the two 512-token exact-lookup
prompts under NInfer. Confirmed decode gains were 52.0% at 2K, 54.0% at 4K,
49.0% at 8K and 49.0% at 16K.
The 512-token ORBIT map effect was also confirmed under Strata.
Same-map screens at 512 tokens, 2K and 4K did not show a 5% NInfer end-to-end
gain. Continue the planned context/workload matrix and broader quality/state
gates before changing release defaults or claiming NInfer acceleration.

Pair-level values, response hashes and memory/clock summaries are in
[`evidence.json`](evidence.json). Raw process captures remain under
`/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/` and are not committed.

## Actual 64K learned-map confirmation (2026-11-01)

A separate seven-pair randomized confirmation followed the passing 64K screen. The task used a tokenizer-verified 65,536-token retrieval/arithmetic prompt with 131,072 configured context. All fourteen strict-NInfer requests returned the exact expected 47-token answer. The learned map improved median decode from 4.5 to 6.3 tok/s (+42.2%; paired bootstrap 95% interval +40.0% to +44.4%). Prompt throughput rose 2.7%, first-visible latency fell 2.7%, client time fell 3.0%, and expert cache hits rose from 21.5% to 48.4%.

Minimum available RAM was 7.25 GiB, maximum sampled swap use 4.66 GiB, and sampled OOM-kill counters remained zero. Observed CPU clocks ranged 730–2,202 MHz and GPU clocks 306–1,301 MHz; clocks were not controlled. EMC clock readback was denied and energy was not measured. This confirms a fixed-map decode effect on this one synthetic 64K fixture. It does not establish semantic quality or general performance across long-context workloads. Pair-level data are in [`evidence.json`](evidence.json); raw captures remain under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task65536-confirmation/`.

## Actual 128K learned-map screen (2026-11-01)

A tokenizer-verified 131,072-token three-position retrieval/arithmetic fixture was screened at 262,144 configured context. Three randomized pairs compared the fixed original and learned 5K GPU maps under strict NInfer, with the same 4,660-entry RAM complement, 6-GiB admission floor and all other runtime controls fixed. All six requests returned the exact expected 47-token response.

The learned map improved median decode from 3.9 to 5.3 tok/s (+35.9%; paired bootstrap 95% screen interval +30.0% to +35.9%). Prompt throughput rose 2.6%, first-visible latency fell 2.5%, client time fell 2.8%, and expert cache hits rose from 21.7% to 48.7%. This met the pre-set 5% median and interval screen gate; a separate seven-pair confirmation is required before treating the effect as confirmed.

Minimum available RAM was 7.21 GiB, maximum sampled swap use 1.07 GiB, and sampled cgroup OOM-kill counters remained zero. Observed CPU clocks ranged 730–2,202 MHz and GPU clocks 306–1,301 MHz; clocks were not controlled. EMC readback was denied and energy was not measured. The result is limited to this synthetic 128K retrieval fixture and does not establish broad quality or general long-context capability. Pair-level values and response hashes are in [`evidence.json`](evidence.json); raw captures remain under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task131072-screen/`.

## Actual 128K learned-map confirmation (2026-11-01)

The independent seven-pair randomized confirmation completed at 262,144 configured context with the same 131,072-token fixture, fixed original/learned GPU maps, shared RAM complement and strict-NInfer settings as the screen. Adaptation and prompt cache remained disabled. All 14 supervised processes passed, and every request returned the exact expected 47-token retrieval/arithmetic response. Its SHA-256 was `428c6ebe1bed005d5e6d7dae8f57f15e923d8be65c6b164487dbec032b3f31db` in all arms.

| Metric | Original map median | Learned map median | Paired median change | Paired bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Decode | 3.9 tok/s | 5.5 tok/s | +38.5% | +36.6% to +41.0% |
| Prompt processing | 108.0 tok/s | 110.6 tok/s | +2.4% | +2.2% to +2.6% |
| First visible token | 1,214.5 s | 1,185.4 s | −2.3% | −2.5% to −2.1% |
| Client request duration | 1,225.6 s | 1,193.5 s | −2.5% | −2.8% to −2.4% |
| NInfer expert hit rate | 21.7% | 48.7% | +27.0 percentage points | same rounded rate in all seven pairs |

Intervals resample the seven within-pair percentage changes (median statistic, 100,000 resamples, seed 42, percentile interval). The decode result confirms the fixed-map performance effect for this exact synthetic 128K fixture; it is not a broad semantic-quality or general long-context qualification.

Minimum available RAM across the 14 processes was 7.22 GiB, above the six-GiB admission floor; maximum sampled swap was 2.96 GiB and sampled cgroup OOM-kill counts were zero. CPU frequencies ranged 729–2,201 MHz and GPU frequencies 306–1,300 MHz; clocks were observed, not controlled. EMC readback was denied and energy was not measured. Pair-level measurements, fixture hashes and response identity are in [`evidence.json`](evidence.json); raw captures remain under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task131072-confirmation/`.


## Actual near-limit 240K learned-map screen (2026-11-01)

A tokenizer-verified 240,286-token three-position retrieval/arithmetic fixture was screened with a 262,144-token context. Three randomized pairs compared the original and learned fixed 5K GPU maps under strict NInfer. Adaptation and prompt cache were disabled, and both maps used the same 4,660-entry RAM complement. All six measured requests passed and returned the exact same 46-token answer (`EARLY=COPPER-ORBIT-482, MIDDLE=SILVER-CANYON-173, LATE=INDIGO-LANTERN-905, SUM=1560`).

| Metric | Original map median | Learned map median | Paired median change | Paired bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Decode | 4.0 tok/s | 5.4 tok/s | +35.0% | +35.0% to +38.5% |
| Prompt processing | 101.5 tok/s | 104.6 tok/s | +3.1% | +2.8% to +3.3% |
| First visible token | 2,368.3 s | 2,297.8 s | −3.0% | −3.3% to −2.7% |
| Client request duration | 2,379.0 s | 2,305.7 s | −3.1% | −3.4% to −2.8% |
| NInfer expert hit rate | 21.5% | 48.2% | +26.7 percentage points | — |

The preset screen threshold (at least 5% median decode improvement with a paired interval above zero) passed, so an independent seven-pair confirmation has started. Minimum available RAM was 7.27 GiB, above the six-GiB admission floor; maximum sampled swap was 2.95 GiB and sampled cgroup OOM kills were zero. CPU/GPU frequencies were observed but uncontrolled; EMC readback was denied and energy was not measured. This is one synthetic near-limit fixture and does not establish semantic quality or general 240K capability. Pair values and response hashes are in [`evidence.json`](evidence.json); raw captures are under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task240286-screen/`.



### Same-map backend screen at 8K

A three-pair screen compared Strata with strict NInfer on the same learned 5K GPU map, same ordered 4,660-entry RAM complement, same Q2_0 model and same 8,192-token retrieval/arithmetic request at 16,384 configured context. Prompt cache, PCIe staging and adaptation were disabled. All six supervised requests passed and returned the identical exact 47-token response. The seeded order placed Strata first in all three pairs.

| Metric | Strata median | NInfer median | NInfer paired change (95% screening interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 7.5 tok/s | 7.5 tok/s | 0.0% (−76.3%, +2.7%) |
| Prompt throughput | 70.8 tok/s | 69.8 tok/s | −1.6% (−2.0%, +6.4%) |
| First visible token | 115.9 s | 117.5 s | +1.5% (−6.0%, +2.1%) |
| Client request duration | 122.0 s | 124.3 s | +1.9% (−5.8%, +18.2%) |

The primary decode median did not meet the 5% useful-effect gate, so no confirmation was run. One NInfer pair decoded at 1.8 tok/s versus 7.6 tok/s for its paired Strata control; the other two NInfer pairs were 7.6 and 7.5 tok/s. All pairs retained the same 47.4% expert hit rate and exact response hash. This outlier is retained, with no causal attribution. Minimum available RAM was 8.93 GiB, peak sampled swap was 1.40 GiB and sampled cgroup OOM-kill counts were zero. Clocks were sampled but not controlled; energy was not measured. This small screen gives no evidence of a useful same-map NInfer advantage at 8K and does not establish backend equivalence. Pair data is in [`evidence.json`](evidence.json); raw captures remain under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task8192-backend-screen/`.

### Same-map backend screen at 16K

A separate three-pair screen compared Strata and strict NInfer with the same learned 5K GPU map on the 16,384-token retrieval/arithmetic request at 32,768 configured context. Both arms used the same Q2_0 artifact, ordered 4,660-entry RAM complement, 128-token prefill chunk, eight pool workers and other launch controls. Prompt cache, PCIe staging and adaptation were disabled. All six supervised requests passed and returned the same exact 47-token answer. The randomized order was Strata-first in pairs 0 and 2 and NInfer-first in pair 1.

| Metric | Strata median | NInfer median | NInfer paired change (95% screening interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 7.2 tok/s | 7.2 tok/s | 0.0% (−1.4%, +2.8%) |
| Prompt throughput | 82.5 tok/s | 82.7 tok/s | +0.1% (−0.1%, +12.8%) |
| First visible token | 198.8 s | 198.3 s | −0.1% (−11.2%, +0.1%) |
| Client request duration | 205.1 s | 204.7 s | −0.04% (−11.0%, +0.1%) |

Decode, the nominated primary metric, was tied at the paired median and its interval included zero; no confirmation was indicated. Both backends recorded a 48.2% expert-cache hit rate. Minimum available RAM was 8.53 GiB, peak sampled swap was 4.25 GiB and cgroup OOM-kill counts were zero. Clocks were sampled but uncontrolled; EMC readback was denied and energy was not measured. The check graded exact task output and did not capture persistent-state fingerprints. This small screen shows no useful same-map NInfer advantage at 16K; it does not establish equivalence. Pair data is in [`evidence.json`](evidence.json); raw captures remain under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task16384-backend-screen/`.

### Same-map backend screen at 32K

A three-pair comparison tested Strata versus strict NInfer on the same learned 5K GPU map with the exact 32,768-token retrieval/arithmetic request at 65,536 configured context. The Q2_0 artifact, ordered 4,660-entry RAM complement, prefill chunk, worker count and other launch settings were matched. Prompt cache, PCIe staging and adaptation were disabled. All six supervised requests passed and returned the identical exact 47-token answer; both backends recorded 48.2% expert hits. Pair order was Strata-first in pairs 0 and 2 and NInfer-first in pair 1.

| Metric | Strata median | NInfer median | NInfer paired change (95% screening interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 6.9 tok/s | 6.8 tok/s | −1.4% (−5.7%, +1.4%) |
| Prompt throughput | 100.5 tok/s | 100.6 tok/s | +0.1% (0.0%, +0.9%) |
| First visible token | 326.7 s | 326.2 s | −0.1% (−0.8%, +0.03%) |
| Client request duration | 333.0 s | 332.8 s | −0.02% (−0.8%, +0.004%) |

The decode median did not meet the 5% useful-effect gate and the interval includes zero, so no confirmation was run. Minimum available RAM was 7.74 GiB; sampled swap peaked at 5.08 GiB and cgroup OOM-kill counts stayed at zero. Clocks were sampled but uncontrolled; EMC readback was denied and energy was not measured. Persistent-state fingerprints were not captured. This screen shows no useful same-map NInfer gain at 32K and does not establish equivalence. Pair-level measurements are in [`evidence.json`](evidence.json); raw captures remain under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task32768-backend-screen/`.

### Same-map backend screen at 64K

A three-pair comparison tested Strata versus strict NInfer with the same learned 5K GPU map on an exact 65,536-token retrieval/arithmetic request at 131,072 configured context. The model artifact, ordered 4,660-entry RAM complement, prefill chunk, workers and other launch controls were matched. Prompt cache, PCIe staging and adaptation were disabled. All six supervised requests passed with the exact same 47-token answer and 48.4% expert-cache hit rate. Pair 0 ran Strata first; pairs 1 and 2 ran NInfer first.

| Metric | Strata median | NInfer median | NInfer paired change (95% screening interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 6.4 tok/s | 6.5 tok/s | +1.6% (+1.6%, +3.1%) |
| Prompt throughput | 107.1 tok/s | 107.8 tok/s | +0.7% (−0.6%, +1.2%) |
| First visible token | 612.3 s | 608.1 s | −0.7% (−1.3%, +0.6%) |
| Client request duration | 619.4 s | 615.1 s | −0.7% (−1.3%, +0.5%) |

The primary decode change was below the 5% useful-effect gate, so no confirmation was run. Minimum available RAM was 7.29 GiB; sampled swap peaked at 3.96 GiB and cgroup OOM-kill counts were zero. CPU/GPU clocks were sampled but uncontrolled; EMC readback was denied and energy was not measured. Persistent-state fingerprints were not captured. This screen shows no useful same-map NInfer gain at 64K and does not establish backend equivalence. Pair data is in [`evidence.json`](evidence.json); raw captures remain under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task65536-backend-screen/`.

### Actual near-limit 240K map confirmation

The independent seven-pair randomized confirmation completed at 262,144 configured context with strict NInfer, adaptation and prompt cache disabled, and the same fixed 5K GPU maps and ordered 4,660-entry RAM complement. All fourteen supervised requests processed 240,286 prompt tokens and returned the same exact 46-token response.

| Metric | Original map median | Learned map median | Paired median change (95% interval) |
| --- | ---: | ---: | ---: |
| Decode throughput | 3.9 tok/s | 5.4 tok/s | +35.9% (+35.0%, +38.5%) |
| Prompt throughput | 101.5 tok/s | 104.5 tok/s | +3.0% (+2.8%, +3.3%) |
| First visible token | 2,367.5 s | 2,300.4 s | −2.8% (−3.1%, −2.7%) |
| Client request duration | 2,378.5 s | 2,308.4 s | −2.9% (−3.2%, −2.8%) |
| NInfer expert hit rate | 21.5% | 48.2% | +26.7 percentage points |

Intervals resample the seven within-pair percentage changes (median statistic, 100,000 resamples, seed 42, percentile interval). Minimum available RAM across the fourteen processes was 7.29 GiB, above the six-GiB admission floor. Maximum sampled swap was 2.97 GiB and sampled cgroup OOM-kill counts were zero. Clocks were observed but not controlled; EMC readback was denied and energy was not measured. This confirms the resident-map effect only for this exact synthetic 240K retrieval/arithmetic fixture; it does not establish broad semantic quality or general 240K capability. Full pair data is in [`evidence.json`](evidence.json); raw captures remain under `/tmp/e6-ninfer-adapt-5k/fixed-map-ORBIT-pp512-tg64/task240286-confirmation/`.

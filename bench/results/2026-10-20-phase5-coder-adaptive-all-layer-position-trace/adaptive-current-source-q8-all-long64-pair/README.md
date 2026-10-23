# Current-source Q8_1 adaptive migration long-chain check — Orin — 2026-10-20

This supervised correctness pair tests the current working-tree build against
the pinned Coder IQ1_M GGUF from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`; shard hashes are recorded in
`campaign.json`. Both services used the same
short-512 → long-2048 → short-512 sequence, 64 generated tokens per request,
prompt-cache capacity 6, and `STRATA_NATIVE_CPU_Q8_1_DOT=all`. One arm delayed
adaptation; the other used cadence 4 with an eight-blob adaptive cap. The
randomized pair ran under separate `MemoryMax=28G` supervisors. This is a
correctness test, not a latency, quality, energy, or quantization comparison.

The fresh CUDA 12.6 / SM87 build has SHA256
`b672187692408e8abcb48beb6ad80282b01954bae819ec48963ac7c6440e4ec9`. It was
built from repository HEAD `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5` plus the
working-tree source changes. The source file hashes used for the relevant
instrumentation and Q8_1 arithmetic are:

```text
8087daa80902be4c98a17191bc57fdbf93e33360ccb124c2c92992eb5337673a  include/strata/core/verify.hpp
f1503b703ea3c4b8c0110f0fab1e3c6fea3c2ae74374f9fe27d973c242361eb4  src/core/verify.cpp
2e53ef273594cc059a95933981937cb7c72eb8e7c464153b5c7c325ff0ed27a7  src/core/expert_source.cpp
b10b75bdd6d444474b1a41cd36378fe3fe05399e8d5cdd396bd644fd42213a50  src/kernels/cpu/native_expert.cpp
8fc4efda11d8a60558cb6ca73c51b71fb426131d8c007b6be8ed7952c7c7b79a  src/kernels/native_expert_parity.cpp
```

Delayed-control recovery reproduced all 64 token IDs, aggregate accepted-prefix
state fingerprints, and per-GDN hashes from its initial short request. Adaptive
recovery differed at 40/64 token IDs and 60/64 accepted-prefix state
fingerprints; the first state difference was prefix 4 (absolute accepted
position 515), where GDN ordinals 13–35 first differed. Q8_1 for all eligible
CPU dots therefore does not eliminate or bound the adaptive-migration drift in
this sequence. The direct log parser validates all 192 accepted-prefix records
per arm against `requests.json` and checks all 36 per-GDN hashes at each record;
its output is `accepted-prefix-analysis.json`.

Both arms passed supervision. Elapsed times were 406.6 seconds (delayed) and
367.7 seconds (adaptive); minimum host and admission availability were 13.78
and 14.12 GiB. All 388 and 351 recorded memory samples respectively showed
zero `high`, `max`, `oom`, or `oom_kill` cgroup events. Clocks were sampled
read-only and were not fixed. Energy was not attributed to requests. Q8_1
decode was slow in this test (about 0.6–1.1 tokens/s), so these elapsed times
are not performance evidence.

At the captured prompt-tail position 511, the initial and recovery verifier
inputs and expert IDs matched in all recorded layers. The route capture has no
CPU activation row for layers 36 and 45; in the other 46 layers, no activation
values differed. Adaptive residency changed owners at 23 layers, while delayed
control had no owner changes. This makes the state drift consistent with
owner-dependent arithmetic under matching sampled inputs, but does not isolate
which changed expert contribution causes the first accepted-prefix mismatch.
The dispatch-to-request mapping is retained in `selected-position-analysis.json`.

The exact campaign, source binary identity, arm order, commands, raw service
logs, token IDs, route captures, one-second memory samples and telemetry are
retained here. Rebuild the candidate with the recorded CUDA 12.6 / SM87
configuration, point `bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7/config.json`
at that binary, then run:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 20261086 --sequence short-long-short --continuations 0 \
  --generated-tokens 64 --native-cpu-q8-1-dot all \
  --output /tmp/adaptive-current-source-q8-all-long64-pair
```

The fresh CUDA build also passed 14 focused CTests covering accepted windows,
verifier and speculative verifier parity, Q8_1 dot/window parity for the
eligible IQ2_S/IQ3_XXS/IQ3_S format pairs, and selector validation. The test
log is `current-cuda-ctest.log`. The full integration Python suite passed
163/163, and `git diff --check` was clean.

The diagnostic selector remains opt-in. This result does not establish a
general drift bound or close Phase 5.

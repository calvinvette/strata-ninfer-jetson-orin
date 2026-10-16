# Q2_0 int8-KV MTP × prompt-length interaction — Orin — 2026-10-16

The prior seven-pair MTP3 confirmations at 512 and 7,501 prompt tokens used
different Strata binary hashes, so they could not estimate a combined workload
interaction. This experiment uses one binary, one Q2_0 model/artifact set, and
a blocked 2×2 design: MTP off or window 3, paired at 512 or 7,501 formatted
prompt tokens in an 8,192-token context. Only the MTP arguments and verifier
window differ. The existing plan and its limits are in [PLAN.md](PLAN.md).

## Three-pair screen

The randomized screen in `screen-1/` completed all 12 arms successfully: three
fresh-service pairs at each prompt length, with no rejected cells. All
retrieval/arithmetic checks passed. The measured binary SHA256 was
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`, matching
the pinned binary. The campaign record retains source commit
`c55e84756e5497e1e1fd9805e815db5859dfa959`, model and pack checksums, per-arm
commands, supervisor telemetry, request results and the fixed schedule.

Median prompt throughput was 43.30 tokens/s baseline versus 38.12 with MTP3 at
512 tokens, and 62.13 versus 57.86 at 7,501 tokens. Median decode throughput
was 5.52 versus 5.94 tokens/s at 512, and 5.00 versus 4.76 at 7,501. The
screen's ratio-of-effects estimate for prompt throughput was +5.8% at the
longer workload relative to the short workload (paired-process bootstrap 95%
interval 0.844–1.150). For decode throughput it was −9.9% (0.815–0.995). The
decode interval narrowly excludes no interaction, while the short screen has
only three pairs and sizable within-cell spread. Client TTFT interaction was
−5.2% (0.868–1.181); client total-time interaction was +5.1% (0.954–1.176).
This is a screening signal, not a performance conclusion or a default-setting
recommendation.

The lowest per-arm minimum host availability was 17.04 GiB; the lowest
admission-availability sample was 9.76 GiB. All arms stayed above the six-GiB
floor, with zero `low`, `high`, `max`, `oom` and `oom_kill` cgroup events.
Observed clocks were dynamic (CPU 729.6–2,201.6 MHz; GPU 306–1,300.5 MHz), and
`tj` ranged from 48.9 to 56.9 °C. EMC readback was unavailable; rail energy is
not attributed to requests. These values and per-request observations are in
`screen-1/analysis.json` and the raw per-arm supervisor records.

The first launch exposed stale candidate-config filenames in campaign
metadata. No measurement ran in those failed launches. The runner now uses one
tested config-path helper for loading, recording and launching both arms. A
second naming mismatch between the confirmation prompt generator and runner
was fixed with a shared tested filename map. The CPU-only campaign design suite
passes 5/5 tests.

## Held-out confirmation

Because the screen suggests a possible decode interaction, new exact-length
held-out prompts were generated after reviewing it. `confirmation/prepared.json`
records tokenizer/template identity and prompt hashes. The short and
near-limit prompts contain distinct planted markers and are exactly 512 and
7,501 formatted tokens. The confirmation runner plan has seven independent
pairs per workload (28 arms) and uses the same binary and model checksums as the
screen. These prompts have been prepared but not yet measured. The screen and
confirmation remain separate; no MTP-by-workload effect is established until
the held-out stage completes and is analyzed.

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

Confirmation attempt 1 ran all 28 arms, and the generic workload harness
reported success for each. Independent analysis accepted the seven near-limit
pairs but rejected all seven short pairs: the short prompt requested a response
template with `SUM=...` without explicitly asking for suffix arithmetic, so
the model did not return the expected numeric sum. This attempt is excluded
from interaction estimates. Its raw campaign, analysis and original prompt
inputs are preserved in `confirm-1/` and `confirmation-attempt1/`.

The prompt generator now explicitly asks for the sum of the three numbers at
the ends of the retrieved codes. The corrected short prompt is still exactly
512 formatted tokens; the near-limit prompt remains 7,501 tokens. The updated
short prompt SHA256 is
`e60c2022729fa4c503ce617b82f6e90202520b97ea257e8977e5c4bf2f3482fb`; the
near-limit prompt hash remains
`1d5e95c1a742a7a7b1df09568017825c412c0ecdb478deb5974a1369544c69c0`. The
campaign design tests pass 6/6. Attempt 2 in `confirm-2/` completed all 28
arms, and analysis passed 14 independent pairs with no rejected cells. Every
short response returned the exact three planted codes and `SUM=1478`; every
near-limit response returned its three exact planted codes. The campaign kept
the same binary and model/artifact checksums as the screen.

In held-out confirmation, median prompt throughput was 36.62 tokens/s baseline
versus 31.44 with MTP3 at 512 tokens, and 62.99 versus 57.62 at 7,501 tokens.
That is a 13.65% and 8.56% slowdown, respectively, by the median paired
candidate/baseline ratio. Median decode throughput changed by +6.00% at 512
tokens (paired 95% interval −0.80% to +8.53%) and +4.82% at 7,501 tokens
(+2.88% to +9.47%). Client total time increased by 7.60% and 8.63%.

The long-over-short ratio of MTP's paired prompt-throughput effects was +5.89%
(independent paired-process bootstrap 95% interval 1.0009–1.0680). This is
borderline evidence that the prompt-throughput penalty is smaller at 7,501
tokens than at 512, while both workloads remain slower with MTP3. Decode-TPS
interaction was −1.11% (0.9480–1.0936), client-TTFT interaction was −5.41%
(0.9376–1.0003), and client-total interaction was +0.95% (0.9784–1.0770);
those intervals include no interaction. The evidence does not support
promoting MTP3 as a default or a general workload recommendation.

Across the 28 arms, minimum host availability was 17.03 GiB and minimum
admission availability was 10.12 GiB, above the six-GiB floor. Cgroup `low`,
`high`, `max`, `oom` and `oom_kill` counters stayed zero. Observed CPU clocks
ranged 729.6–2,201.6 MHz, GPU clocks 306–1,300.5 MHz, and `tj` 49.8–57.9 °C.
EMC readback remained unavailable. Named rail energy is retained as board-rail
diagnostics, not request-attributed energy.

This completes the MTP × prompt-length screen and held-out confirmation for
these prompts, model and profile. Phase 6 remains open for its other planned
interactions; these findings do not close the broader optimization phase.

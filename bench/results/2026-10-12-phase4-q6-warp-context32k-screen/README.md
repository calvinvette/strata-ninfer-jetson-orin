# Q6_K warp dequantization at 32K configured context — Orin — 2026-10-12

This extends the opt-in `STRATA_Q6K_WARP_DEQUANT=1` path to a new configured
context and synthetic incident-log prompt. The candidate binary SHA256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`. Both
arms used the same local IQ1_M model, Q2_0 expert representation, MTP pack,
3,000 requested cache slots (3,903 observed), FP16 KV, 32,768-token context,
speculation window 4, prefill chunk 64, eight pool workers, and disabled CPU
prefill sharing. The only arm difference was the candidate environment flag.
Model artifacts remain under `~/models/`.

The three-pair screen passed all six requests with matching warmup and measured
text, token counts, speculation counts, and cache capacity. It found median
request time −6.38% and prompt time −7.11% for the candidate; decode intervals
spanned zero. After a separate traced state pair matched, seven new randomized
same-day pairs were run for confirmation. All 14 arms passed the six-GiB
supervisor, with minimum host availability 13,282,598,912 bytes (12.37 GiB).

| Measure | Candidate median paired delta | Paired bootstrap 95% interval |
| --- | ---: | ---: |
| Client request elapsed | −5.96% | −7.05% to −4.34% |
| Engine prompt | −6.89% | −7.13% to −4.98% |
| Engine decode | +0.46% | −1.38% to +2.04% |

Intervals resample seven complete pair deltas 200,000 times with fixed seeds;
the exact samples are in `confirmation-analysis.json`. All seven pairs matched
warmup text, measured output text, prompt/completion counts and observed expert
and conversation-cache sizes. Six pairs also matched draft and accepted-draft
counts; one pair differed by one accepted draft (84 baseline versus 85
candidate). That pair's baseline request was a slow timing outlier and is
retained. Because decode timing is exposed to that speculation-count difference
and its interval spans zero, the repeatable prompt-time reduction is the
clearest runtime result. This does not isolate task quality.

A separate one-pair trace-enabled state check at the same prompt and context
matched generated text, all four accepted-prefix commits, all full-state records
and the final GDN fingerprints. Minimum host availability was 12.56 GiB for
baseline and 12.33 GiB for candidate. State hashing was excluded from timing
arms.

CPU clocks varied from 729 to 2,201 MHz; tegrastats reported GPU utilization
from 0 to 99%, but GPU and EMC clock rates were unavailable. No request-scoped
energy was measured. The prompt is synthetic and padded to exactly 2,048
formatted tokens; task-quality scoring and other workload classes remain
untested. This supports the candidate for continued opt-in qualification at
this cell only; it does not justify default dispatch.

The first two campaign setup attempts are retained separately and excluded:
the first prompt builder could not form an exact token count, and the second
runner lacked generated config files. Neither launched an engine. The successful
screen and confirmation are under `campaign-valid/` and `campaign-confirm7/`;
the traced correctness check is under `state-check/`. Recompute confirmation
statistics with `python analyze_confirmation.py`.

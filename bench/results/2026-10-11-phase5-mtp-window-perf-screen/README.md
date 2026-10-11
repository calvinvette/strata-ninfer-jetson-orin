# Native MTP window decode screen

This randomized same-day screen compared native MTP windows 2, 3 and 4 with
MTP off on Orin using the prepared `pp512+tg64` request. It used three paired
blocks, one warmup and one measured request per fresh supervised process, no
trace instrumentation, prompt cache disabled, and CPU prefill sharing disabled.
The model, tokenizer, draft vocabulary, executable and all non-MTP arguments
were checked across each pair. Actual expert slots and KV format matched.

All 12 processes and measured requests passed. The API response content was
identical within each off/window pair. MTP accepted 27/36, 33/60 and 36/81
drafted tokens for windows 2, 3 and 4, respectively. Median decode throughput
was 7.512 tokens/s with MTP off, versus 7.074, 5.889 and 5.077 tokens/s. The
median paired deltas were **−5.87%**, **−21.67%** and **−32.44%**. The harness's
bootstrap intervals are −6.03% to −5.77%, −21.67% to −21.61%, and −32.47% to
−32.44%; they use only three request pairs and are screening intervals, not
confirmation evidence. The result is a repeatable negative decode result for
this request shape, not a general MTP conclusion. No window is promoted.

Median end-to-end request time increased by 2.34%, 10.56% and 18.05%, while
TTFT changes were +0.14%, +0.86% and +0.92%. Minimum sampled host
`MemAvailable` across all runs was 13.48 GiB, above the required six-GiB floor.
tegrastats recorded changing CPU frequencies and changing power readings; GPU
clocks were not held fixed. The paired randomized ordering reduces some drift,
but this small screen does not qualify energy/token or fixed-clock performance.
No quality, persistent-state, cancellation, long-output or held-out-prompt
claim follows from this timing run.

The full raw process results, request records, server configurations,
capabilities and telemetry are retained by block and window in this directory.
`campaign.json` contains all paired samples and checks. The reproducible runner
is [`mtp_window_screen.py`](../../../tools/integration/mtp_window_screen.py).
The integration Python suite passed 86/86 after this runner was added.

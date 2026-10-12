# Q2_0 captured versus eager decode screen — 2026-10-12

This is a three-pair screening comparison of captured decode and the opt-in
`--no-capture` eager routed-expert path, with MTP disabled and with MTP window 2.
The runs used the integrated Q2_0 pack and PLE artifact under
`~/models/strata-orin-validation/`. The exact binary SHA256 is recorded in
`screen-summary.json`; each pair used independent processes and same-day
randomized order.

## Workloads and result

Each measured request generated eight tokens from the same prepared prompt in
its pair. Prompt lengths were 512 and 2,048 tokens, with 8K configured context,
3,000 expert-cache slots, prefill chunk 64, zero CPU-prefill sharing and
`--spec 2`. The MTP2 arm additionally used the local runtime draft artifact with
`--mtp-max-t 2`. Each process warmed the 512/64 and 2,048/128 workload cells
before measurement. Warmup output is retained and excluded from the rates below.

All three pairs matched the generated text in each cell. In every MTP2 request,
both controls reported four drafted and four accepted tokens. That is evidence
for this short prefix only; the separate accepted-prefix/state checks remain the
correctness gate for speculation.

| MTP | Prompt | Captured decode, tokens/s (three pairs) | Eager decode, tokens/s (three pairs) | Median eager/captured rate |
| --- | ---: | --- | --- | ---: |
| Off | 512 | 11.6, 9.1, 8.3 | 12.9, 7.8, 7.8 | −6.0% |
| Off | 2,048 | 8.5, 12.6, 11.8 | 7.4, 10.7, 10.0 | −15.1% |
| 2 | 512 | 9.0, 8.4, 6.5 | 11.6, 7.9, 8.2 | +26.2% |
| 2 | 2,048 | 7.1, 9.5, 11.2 | 8.1, 11.3, 9.5 | +14.1% |

These rates are server timing summaries from one eight-token request per process
and cell. They are noisy screening observations, not an end-to-end performance
qualification or evidence to change defaults. MTP-off eager decode was slower
at both prompt sizes by the paired median; MTP2 eager results varied by pair.
The campaign did not collect an adequate number of output tokens for a held-out
confirmation or a reliable uncertainty interval.

## Environment and limits

The runs were supervised under a 28 GiB cgroup ceiling, with the ordinary six
GiB host-availability floor and read-only CPU/GPU/EMC clock observations. The
lowest observed host availability was 17.04 GiB; lowest admission headroom was
7.32 GiB. Dynamic clocks were not controlled. Raw tegrastats, memory, engine,
request and supervisor records are retained per process. Board energy was not
measured; rail readings are not process-attributed. The capture path is the
control, and model artifacts are unchanged between controls.

The first MTP-off harness launch is retained in `mtp-off/`: it stopped after
startup because the warmup and measured cell counts differed. It made no API
request and contributes no measurement. The corrected retry is `mtp-off-retry/`.
All six corrected MTP-off and six MTP2 supervisor runs exited successfully.

This screen does not close Phase 5. Longer accepted-prefix chains, rejection
patterns, termination and cancellation transactions, and held-out graph/eager
performance confirmation remain open. It does not reopen or change Phase 3's
Q2_0 scoped closeout.

## Files

- `screen-summary.json` contains paired rates, text checks, MTP counters, memory
  minima and the binary identity.
- `mtp-off/` contains the failed no-request harness attempt.
- `mtp-off-retry/` and `mtp2/` contain corrected raw controls and telemetry.
- The root JSON workload/config files record the explicit launch and workload
  definitions.

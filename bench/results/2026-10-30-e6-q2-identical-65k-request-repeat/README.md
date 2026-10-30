# Current-source identical 65K NInfer repeat

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is a state-repeatability
diagnostic, not a backend comparison or performance result.

## Setup

One strict-NInfer server process handled two identical API requests. Each used
the same 65,536-token prompt (message-text SHA-256
`d6705c01b65da7b7dd39d268d3ea0d0d0b743bbf5631210aa4866caeee9bc16d`), a
131,072-token context, and a one-token generation limit. Prompt caching and
PCIe staging were disabled. The service reported zero cached prompt tokens
for both requests. The active source revision was `47a921ec2e5a57e3884e0f497487ff4dd0da045b`;
the executable SHA-256 was
`28fa55792ad615fd1b806dc5bd903fe5c597be95bc26852c953127c84bb0090f`.
`STRATA_PROMPT_BOUNDARY_STATE_HASH=1` and `STRATA_STATE_HASH=1` were enabled,
with full tracing disabled.

## Result

Both requests passed and returned the same one-token response, `A`. The
prompt-boundary fingerprints matched exactly before either generated-token
commit:

| State field | Both requests |
| --- | --- |
| GDN | `85907b6a2b85d24e` |
| PLE | `df3795d240365f69` |
| Tail | `c4a5d96bb5c4e077` |
| Pooled | `daf9928c718c7b33` |
| KV | `0552810263e21418` |
| MTP | `14650fb0739d0383` |
| Stale | `14650fb0739d0383` |
| Dead | `40ccf57e6c30218e` |
| Pooled full | `f2e8d94d3fe3944a` |
| PLE previous tokens | `271,248069` |

The final persistent-state fingerprints also matched. Prompt processing took
752.9 seconds (87.0 tokens/s) and 749.1 seconds (87.5 tokens/s); those
instrumented single-process readings are included only to identify the run and
must not be used as performance evidence. Each one-token generation took
about 19 seconds. The engine reported 8,978 MiB shared RAM available after
startup; no time-series memory supervisor, energy measurement, or clock log
was collected, so this run does not establish the six-GiB floor over the full
request or any broader resource qualification.

## Interpretation and limits

This confirms that the current NInfer path can reset and reproduce this exact
65K request twice in one process when prompt and generation limits match. It
does not resolve the earlier pair where a 128-token warmup and 32-token
measured request had different boundary fingerprints within each backend, and
does not establish Strata/NInfer state parity or task quality. The next
diagnostic should repeat the same prompt twice with an identical 32-token
generation limit to check whether the earlier request-shape difference
matters. E6 and E7 remain open.

Raw logs and request results are kept locally under
`/tmp/e6-65k-current-repeat/`; no model data or raw response dump is committed.

# 65K NInfer repeat with immediate reset fingerprints

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is an instrumented,
same-backend state diagnostic; it is not a performance or quality result.

## Setup

One current-source strict-NInfer process handled two identical requests. Both
used the same 65,536-token prompt (message-text SHA-256
`d6705c01b65da7b7dd39d268d3ea0d0d0b743bbf5631210aa4866caeee9bc16d`),
temperature 0, 32-token generation limit and a 131,072-token context. Prompt
cache and PCIe staging were disabled; both responses reported zero cached
prompt tokens. The current CUDA executable was built from commit `fc381759`
with SHA-256
`eec447aba96c06a1a905b8fef94440f9919e300fc4f007f0b54df83b88162cf5`.
`STRATA_REQUEST_RESET_STATE_HASH`,
`STRATA_PROMPT_BOUNDARY_STATE_HASH` and `STRATA_STATE_HASH` were enabled, with
full tracing disabled.

## Result

The immediate post-reset fingerprint was identical for both requests:

| Reset field | Both requests |
| --- | --- |
| GDN | `2d2b4c71fb470383` |
| PLE | `0b6b00a4dd808383` |
| QSA tail | `edd71f53c31aee9b` |
| QSA dead | `5c42fcd39eb3da43` |
| QSA pooled index state | `523841e80930e77b` |
| PLE previous tokens | `-1,-1` |

After both requests processed the full prompt, the boundary fingerprints
differed:

| State field | Request 1 | Request 2 | Match |
| --- | --- | --- | --- |
| GDN | `85907b6a2b85d24e` | `5c793b8a70da9a04` | No |
| PLE | `df3795d240365f69` | `df3795d240365f69` | Yes |
| Tail | `c4a5d96bb5c4e077` | `c4a5d96bb5c4e077` | Yes |
| Pooled | `daf9928c718c7b33` | `768df0029b886add` | No |
| KV | `0552810263e21418` | `a9df73b118768bd5` | No |
| MTP | `14650fb0739d0383` | `14650fb0739d0383` | Yes |
| Stale | `14650fb0739d0383` | `14650fb0739d0383` | Yes |
| Dead | `40ccf57e6c30218e` | `40ccf57e6c30218e` | Yes |
| Pooled full | `f2e8d94d3fe3944a` | `ed5187a71d99941c` | No |
| PLE previous tokens | `271,248069` | `271,248069` | Yes |

Both requests passed and generated 32 tokens. Response hashes were
`9eb4258bd7960b7d229788732574e77e3d1de986c5ac8c1a071e5a97521f9101` and
`aa244120f27dce23fbd847125de7ca2347e6c0ad9e3bd8f3cee49cf447ce96c9`.
Prompt processing took 751.0 and 750.4 seconds (87.3 tokens/s each); these
synchronized diagnostic timings are not performance evidence. The engine
reported 9,071 MiB shared RAM available at startup with a 6,144 MiB physical
RAM headroom setting. Continuous memory, clock and energy telemetry were not
collected.

## Interpretation and limits

The reset state recorded immediately after `session_zero` is identical. The
state difference appears after prompt evaluation and before the first
generated-token commit. This narrows the lifecycle question, but does not
identify a kernel or establish whether the variation is caused by prompt
execution, asynchronous scheduling, or another request-order-sensitive path.
The extra device synchronization and host copies can affect execution; both
responses also differed from each other. The matching Strata-backend repeat
without this hook already showed that this behavior is not unique to NInfer.
E6 and E7 remain open. Next localize the earliest prompt position where state
differs under matched capture settings.

Raw logs and response bodies remain under
`/tmp/e6-65k-ninfer-reset-state-repeat/` and are not committed.

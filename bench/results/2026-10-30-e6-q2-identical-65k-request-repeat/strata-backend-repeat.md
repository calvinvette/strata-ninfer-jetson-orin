# Matched 65K/32 Strata-backend repeat

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is a same-backend state
repeatability control against the strict-NInfer run, not a performance or
quality qualification.

## Setup

One current-source CUDA process using Strata's expert backend served the same
65,536-token prompt twice with temperature 0 and a 32-token generation limit.
It used a 131,072-token context, disabled prompt cache and PCIe staging, and
reported zero cached tokens for both requests. All settings matched the
strict-NInfer repeat apart from `--expert-backend`. Source revision was
`47a921ec2e5a57e3884e0f497487ff4dd0da045b`; executable SHA-256 was
`28fa55792ad615fd1b806dc5bd903fe5c597be95bc26852c953127c84bb0090f`.

## Result

Both requests passed and consumed 65,536 prompt tokens. Their prompt-boundary
fingerprints differed in the second request:

| State field | Request 1 | Request 2 | Match |
| --- | --- | --- | --- |
| GDN | `85907b6a2b85d24e` | `f123dd046960f8c5` | No |
| PLE | `df3795d240365f69` | `df3795d240365f69` | Yes |
| Tail | `c4a5d96bb5c4e077` | `e242be5d94cea00d` | No |
| Pooled | `daf9928c718c7b33` | `2bb2d56266d9d7da` | No |
| KV | `0552810263e21418` | `1cf7c5c63e5907bc` | No |
| MTP | `14650fb0739d0383` | `14650fb0739d0383` | Yes |
| Stale | `14650fb0739d0383` | `14650fb0739d0383` | Yes |
| Dead | `40ccf57e6c30218e` | `40ccf57e6c30218e` | Yes |
| Pooled full | `f2e8d94d3fe3944a` | `da782e97dca03cd3` | No |
| PLE previous tokens | `271,248069` | `271,248069` | Yes |

Both responses passed the API checks. The first response hash was
`9eb4258bd7960b7d229788732574e77e3d1de986c5ac8c1a071e5a97521f9101`; the
second was `a26d04bc550960640df59af02a16ebe5def41f6d75bc410da0b2188dacbb7621`.
The two prompt rates were 87.0 and 87.5 tokens/s; these synchronized
diagnostic readings are not performance evidence. The engine reported 9,039
MiB shared RAM available at startup with a 6,144 MiB physical RAM headroom
setting. No continuous memory, clock or energy telemetry was captured.

## Interpretation and limits

The second-request divergence reproduces with Strata's expert backend. The
same two response hashes occur in the same order in the matched strict-NInfer
run, even though the backends' second prompt-boundary fingerprints are
different. This makes an NInfer-only dispatch explanation less likely and
points toward an order-sensitive path shared by the service/runtime or model
evaluation. The data do not identify a root cause. `session_zero` runs on the
no-resume path, but no fingerprint was taken immediately after the reset;
that is the next diagnostic. E6 and E7 remain open.

See the paired [strict-NInfer repeat](32-token-repeat.md). Raw logs and
responses remain local under `/tmp/e6-65k-strata-repeat-32/`.

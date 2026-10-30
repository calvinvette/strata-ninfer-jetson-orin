# Matched 65K/32 NInfer repeat

Date: 2026-10-30. Hardware: Jetson AGX Orin. This is a same-backend state
repeatability diagnostic, not a performance or quality qualification.

## Setup

One current-source strict-NInfer process served two identical requests. Both
used the same 65,536-token prompt (message-text SHA-256
`d6705c01b65da7b7dd39d268d3ea0d0d0b743bbf5631210aa4866caeee9bc16d`), a
131,072-token context, temperature 0, and a 32-token generation limit. Prompt
cache and PCIe staging were disabled; both responses reported zero cached
prompt tokens. The engine used `--prefill 128`, `--spec 2`, 3,000 expert cache
slots and a six-GiB resident budget. Source revision was
`47a921ec2e5a57e3884e0f497487ff4dd0da045b`; executable SHA-256 was
`28fa55792ad615fd1b806dc5bd903fe5c597be95bc26852c953127c84bb0090f`.
Prompt-boundary and final state hashes were enabled, with full tracing off.

## Result

Both API requests passed and consumed exactly 65,536 prompt tokens. The first
prompt-boundary fingerprint matched the same backend's earlier 65K/one-token
repeat. The second prompt-boundary fingerprint differed:

| State field | Request 1 | Request 2 | Match |
| --- | --- | --- | --- |
| GDN | `85907b6a2b85d24e` | `edd090f65060e1bb` | No |
| PLE | `df3795d240365f69` | `df3795d240365f69` | Yes |
| Tail | `c4a5d96bb5c4e077` | `12b1cbce6bc413c8` | No |
| Pooled | `daf9928c718c7b33` | `6179f5323538c6a8` | No |
| KV | `0552810263e21418` | `3588fdb0f940b12c` | No |
| MTP | `14650fb0739d0383` | `14650fb0739d0383` | Yes |
| Stale | `14650fb0739d0383` | `14650fb0739d0383` | Yes |
| Dead | `40ccf57e6c30218e` | `29130225db01cb50` | No |
| Pooled full | `f2e8d94d3fe3944a` | `a508103dccaa7bab` | No |
| PLE previous tokens | `271,248069` | `271,248069` | Yes |

The first response text hash was `9eb4258bd7960b7d229788732574e77e3d1de986c5ac8c1a071e5a97521f9101`;
the second was `a26d04bc550960640df59af02a16ebe5def41f6d75bc410da0b2188dacbb7621`.
The outputs began alike but diverged within the response. Prompt processing
took 751.0 seconds (87.3 tokens/s) and 748.1 seconds (87.6 tokens/s); these
synchronized diagnostic runs are not performance measurements. Minimum
available RAM over time, clocks and energy were not captured. At engine
startup it reported 8,991 MiB shared RAM available and a 6,144 MiB physical
RAM headroom setting.

## Interpretation and limits

This reproduces long-context state and output divergence within one NInfer
process even with identical prompt and generation settings, cache disabled,
and the no-resume reset path. Source inspection confirms `session_zero` runs
before each prompt when `resume == 0`; it clears the main and staged session
state. The capture therefore places the observed difference after reset and
by the end of prompt evaluation, but it does not distinguish request-history
effects from nondeterministic computation and does not identify an NInfer
kernel as the cause. The one-token matched repeat passed, while the earlier
128-token-warmup/32-token-measured pair also diverged. Next run the same
65K/32 repeated request under Strata's expert backend to check whether the
behavior is shared. E6 and E7 remain open.

Raw logs and outputs are local under `/tmp/e6-65k-current-repeat-32/` and are
not committed.

# Corrected 4K / 557-token Q2_0 repeat screen

Date: 2026-10-25. This randomized three-pair repeat checks an isolated
4K-capacity / 557-prompt-token / 64-output NInfer timing outlier from the
corrected-kernel context screen. Each arm started a fresh service, used the
same Coder Q2_0 artifact and 3,000-slot profile, and received one warmup plus
one measured request. Arm order was randomized within each pair. The CUDA
server binary SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75`.

| Pair | Order | TTFT change | Client completion change | Output / resident map |
| ---: | --- | ---: | ---: | --- |
| 1 | Strata, NInfer | −1.08% | −0.67% | match / match |
| 2 | Strata, NInfer | −2.29% | −2.29% | match / match |
| 3 | NInfer, Strata | −0.72% | −0.13% | match / match |
| Median paired change | — | −1.08% | −0.67% | all match |

The repeat did not reproduce the original 44-second NInfer TTFT outlier; all
three NInfer measurements were close to their paired Strata controls. The
effect is below the predeclared 5% screening threshold, so no seven-pair
confirmation is warranted for this cell. This is a small screen, not a
performance qualification. Minimum available physical/admission memory was
17.85 GiB; the six-GiB headroom floor and separate three-GiB workspace reserve
were retained. Clocks were sampled read-only and not controlled; EMC access
was unavailable, and energy was not attributed. Raw request results,
residency maps, launcher commands and per-process supervisor telemetry are in
[`retry1/`](retry1/).

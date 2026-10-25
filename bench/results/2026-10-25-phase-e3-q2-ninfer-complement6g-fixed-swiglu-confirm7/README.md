# Seven-pair corrected-kernel 6-GiB staging confirmation

Date: 2026-10-25. Before this test, [the plan](../../../../docs/integration/NINFER_EXPERT_EXECUTION_PLAN.md)
pre-registered TTFT as the primary metric for the prompt-to-first-token
staging effect, with a 5% useful-effect threshold. Client completion was the
secondary metric, with a maximum tolerated regression of 5%. Seven independent
randomized process pairs used the same Q2_0 Coder artifact, 3,000 resident
slots, 6-GiB complement, 3-GiB workspace reserve, 8K context cap, MTP-2,
128-token prefill and 8 workers. Each fresh service ran one warmup and one
measured short `1+1` request.

The model is `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0`, split across
`Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf` (37,623,740,192 bytes)
and `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf` (28,800,138,432
bytes). The tested service binary SHA256 is
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75`.

| Metric | Median paired change | Paired bootstrap 95% interval | Decision |
| --- | ---: | ---: | --- |
| TTFT (primary) | −5.96% | −6.23% to −5.80% | useful-effect gate passed |
| Client completion (secondary) | −4.17% | −4.40% to −4.00% | improved; no regression |

The interval bootstraps whole independent paired processes (100,000 draws,
seed 20261028). All seven pairs used the same resident-map hash and had exact
measured-response hash matches. **All seven warmup response hashes differed
between arms**; the matched measured requests are the timing observations, and
the warmup differences are retained as a qualification caveat. The separate
512-token held-out answer and final-state check passed with the corrected
kernel. Minimum available memory was 11.37 GiB. Read-only GPU clock samples
ranged from 306 to 1,300.5 MHz (median 1,300.5 MHz); EMC was unavailable, and
energy was not attributed.

This qualifies the TTFT effect for this one short request/profile. It does not
close E6 across context sizes or model variants, and it does not establish a
general release profile. The large grouped 64/128-token operator screen also
remains slower than Strata. Raw paired measurements, maps, scripts and
supervisor telemetry are retained in [`staged-screen/`](staged-screen/) and
`supervisor/`.

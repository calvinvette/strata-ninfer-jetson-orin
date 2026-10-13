# IQ1_M graph capture × MTP screen — Orin — 2026-10-14

This experiment screened eager versus captured decode with MTP off and MTP4,
then ran a seven-pair held-out MTP4 confirmation. It uses the local Flash-Next
IQ1_M validation pack and runtime draft artifact under
`~/models/strata-orin-validation/`; no model artifacts are stored in Git. The
same candidate binary was used throughout (SHA256
`2403c73bfde5b942022266e1f77502e7b53b418a7d700c5bf5cd5a3826989b77`).

The workload is a distinct, exactly 2,048-token watershed incident prompt with
128 generated tokens, 8K context, FP16 KV, 3,000 requested expert-cache slots,
prefill chunk 64, zero CPU-prefill sharing, and accepted-only adaptation every
four published tokens. Each timing arm used a fresh service and a separate
512-token/one-output warmup. MTP4 used the same draft pack, spec window,
cache policy and adaptation policy in both routes. The eager route adds
`--no-capture`. CPU/GPU/EMC clocks were observed, not controlled; EMC access
was denied. Energy was not process-attributed.

Before timing, captured and eager state traces were run on this held-out prompt
for MTP off/2/3/4. All four generated token sequences and final persistent
states matched exactly. Every shared accepted-prefix checkpoint matched: 128,
76, 66 and 48 checkpoints for MTP off/2/3/4. MTP2/3/4 offered and accepted
64/52, 81/62 and 112/80 drafts in each route. The supervised traces passed;
minimum host availability was 13.38 GiB for captured and 13.39 GiB for eager.

The three-pair screen showed no MTP-off request benefit (eager paired median
+0.88%). For MTP4, the eager paired median was −10.55%, driven by two large
decode improvements and one reversal. The held-out confirmation did not
reproduce that result:

| Metric | Captured median | Eager median | Paired median change, eager vs captured | 95% paired bootstrap interval |
| --- | ---: | ---: | ---: | ---: |
| Request time (prompt + decode) | 100.559 s | 100.273 s | −0.57% | −1.10% to +0.69% |
| Prompt time | 91.748 s | 91.534 s | −0.58% | −1.22% to +0.53% |
| Decode time | 8.573 s | 8.490 s | −0.97% | −1.33% to +0.23% |
| Client first-visible delta | 91.825 s | 91.622 s | −0.59% | −1.19% to +0.53% |

There were seven randomized same-day pairs; all 14 arms passed supervision,
generated 128 output tokens, and accepted 81 of 113 drafts. Output text matched
within all seven pairs. The paired intervals include no change and do not meet
the project's 5% promotion threshold. The minimum host availability and
effective admission headroom across these arms were both 13.12 GiB; there were
no supervisor OOM events. Retain graph capture as the current route; no default
or opt-in profile changes follow from this experiment. This result applies to
this model, prompt, context, cache and accepted-only policy only.

One initial confirmation command stopped before inference because its warmup
path did not exist. That failed setup attempt is retained in
`watershed-mtp4-confirm7/` and excluded. The corrected seven-pair campaign is
in `watershed-mtp4-confirm7-rerun/`. The captured/eager traces are in
`watershed-state-captured/` and `watershed-state-eager/`; three-pair screens
are in `mtp0/` and `mtp4/`. All raw request records, randomized campaign plans,
telemetry, clocks and supervisor samples are retained in those directories.

The timing command was:

```sh
python3 tools/integration/run_paired_controls.py \
  --baseline-config bench/results/2026-10-14-phase6-iq1-graph-mtp-screen/configs/captured-mtp4.json \
  --candidate-config bench/results/2026-10-14-phase6-iq1-graph-mtp-screen/configs/eager-mtp4.json \
  --workloads bench/results/2026-10-14-phase6-iq1-graph-mtp-screen/workloads-watershed.json \
  --output bench/results/2026-10-14-phase6-iq1-graph-mtp-screen/watershed-mtp4-confirm7-rerun \
  --blocks 7 --seed 202610143 \
  --warmup-workloads bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/warmup-workloads.json \
  --no-trace --sample-clocks
```

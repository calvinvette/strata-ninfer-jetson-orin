# Three-pair resident Q2_0 service screen

Date: 2026-10-25, Jetson AGX Orin, CUDA 12.6, SM87. This is the planned
three-block screening stage, not a seven-block performance confirmation.

## Controls

Each process used the same Release executable (`strata` SHA256
`527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`), Q2_0
model/PLE/profile, tokenizer, 8K context, 3,000 profile-filled expert slots,
FP16 KV, prefill 128, eight workers, `--spec 2 --suffix-draft 0`, mmap expert
source and other launch flags. Draft counters were `0 of 0`; MTP was inactive.
The candidate added `--expert-backend ninfer --expert-backend-strict`; control
used the default Strata backend. Each fresh service ran one identical warmup and
then one measured `1+1` request, temperature 0, max 48 tokens. Candidate/control
order was randomized by a fixed seed. The measured prompt was 55 tokens and the
completion was 29 tokens in every run.

All six startup residency-map files have SHA256
`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7` and contain
3,000 resident model-expert-to-slot mappings. All measured output text hashes
match (`18e649c52e8a6a942bfb6c486a4da267fc7ca05faaf55c831ea4b35372df848e`).
The reported GPU cache hit counts are near, but not exactly, matched; the logs
show a 0.2 percentage-point difference. The same prompt/output alone does not
prove identical internal route IDs.

## Results

| Pair | Backend order | Prompt time, NInfer / Strata | Decode time, NInfer / Strata | Client total, NInfer / Strata | GPU hits, NInfer / Strata |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | NInfer then Strata | 7.943 / 7.681 s | 3.354 / 3.145 s | 11.301 / 10.829 s | 57.4% / 57.2% |
| 2 | NInfer then Strata | 6.321 / 5.945 s | 3.398 / 3.151 s | 9.722 / 9.098 s | 57.4% / 57.2% |
| 3 | Strata then NInfer | 6.046 / 5.933 s | 3.356 / 3.129 s | 9.405 / 9.065 s | 57.4% / 57.2% |

Median paired change for NInfer versus Strata was **+3.4% prompt latency,
+7.3% decode latency, +4.4% client completion time, and +3.5% client TTFT**.
Positive latency change is slower. Each of the three individual blocks was
slower with NInfer on all four measures. The sample is too small for a
performance claim or confidence interval; it is a consistent negative screen
that fails the useful-effect gate and does not justify seven-block confirmation
for this revision.

The service returned identical output text in all measured runs. This is only a
basic functional check, not an independent model-quality evaluation. Host
headroom at startup remained at the declared 6 GiB floor (the service log showed
about 18 GiB shared RAM available); actual Orin GPU clock readback and energy
were unavailable. No clocks were changed.

## Evidence files

`results.json` contains per-run request timing, output hash, order and residency
hash. Each paired `*.log` has the engine's prompt/decode timing, draft counters,
cache hit counts, startup memory and NInfer dispatch log. The matching
`*.residency.csv` files are the resident-map artifacts. Per-run JSON files are
the service configurations; they contain local model paths but no model data or
credentials. `../run_paired_service_screen.py` reproduces this screening setup.

## Decision

Do not promote this grouped Q2_0 schedule as an optimization and do not change
the default backend. The separate operator screen found 85.7 us median for
NInfer versus 24.5 us for Strata on one resident token (3.50x latency). Optimize
or reject this schedule before any confirmation campaign. A follow-up should
measure actual kernel breakdown and reduce the candidate's extra compute/launch
cost. Service comparison remains a natural-request screen; exact per-layer
route IDs were not captured, and the 26-hit difference confirms some route
variation remains despite identical outputs and residency.

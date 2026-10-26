# Staged Strata/NInfer backend performance screen

Date: 2026-10-26. Hardware: Jetson AGX Orin 32 GB, SM87, CUDA 12.6.
Model: Qwen3.8-Flash-Next GSQ RCO Q2_0, from the two local GGUF shards and
Q2_0 pack referenced by the saved configs. Binary SHA256:
`3a8133abbbe83dce0ec87473d5843f8cb59d9e59ed276198ab008747ff333b90`;
source commit: `68de59ab2c6736ca328c83afabe2138123cd7051`.

## Pre-registered screen

- Compare Strata staged (`--expert-backend strata --pcie-frac 1.0`) with strict
  NInfer staged (`--expert-backend ninfer --expert-backend-strict --pcie-frac
  1.0`). All other arguments, source, model, cache, tokenization and request
  body are identical. Each process gets an independent loopback server.
- Use the exact held-out 2,048-token retrieval/arithmetic task and request up to
  48 completion tokens. Fresh prefill, prompt cache disabled; one same-request
  warmup per process, then one measured streamed request. Three randomized
  independent process pairs, seed `870126`.
- Primary metric: engine `predicted_per_second` (decode tokens/s). Secondary:
  client total latency and client TTFT; report prompt throughput as context.
- Screen gate: at least 5% median paired improvement in decode rate, with all
  three pairs favoring the candidate. Client total may not regress by more than
  5%. Require matching measured response hashes, final state fingerprints,
  resident-map hashes and staged-read counts. These three pairs are screening;
  a passing screen would require an independent seven-pair confirmation with a
  paired bootstrap interval before any performance claim.
- No clocks or services are changed. Require at least 6 GiB available memory;
  retain supervisor memory, clock and tegrastats records. Any failed request or
  memory-floor breach stops the campaign and is reported as failed.

Full staged Strata and NInfer backends already passed exact output and state
parity on this workload. This screen asks whether the NInfer backend changes
end-to-end performance when the staged route and all other policy are held
fixed. The 2K workload is one cell only; it does not qualify other contexts,
models or staging budgets.

## Results

All six supervised processes and twelve warmup/measured requests passed. Each
response contained 47 completion tokens and the exact retrieval answer. Within
every pair, measured output hashes and final state fingerprints matched. The
two per-request expert-cache rows were identical across every process: warmup
had 3,268 staged reads and the measured request had 1,621, out of 22,560 routed
entries each. Minimum available memory ranged from 11.43 to 11.54 GiB; the
6-GiB floor was retained.

| Pair | Order | Decode TPS, NInfer / Strata | Paired decode TPS change | Client total, NInfer / Strata | Paired client latency change | TTFT, NInfer / Strata |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | NInfer, Strata | 9.2 / 8.8 | +4.55% | 56.883 / 59.156 s | −3.84% | 51.168 / 53.244 s |
| 1 | NInfer, Strata | 8.8 / 8.9 | −1.12% | 56.868 / 55.416 s | +2.62% | 50.973 / 49.723 s |
| 2 | Strata, NInfer | 9.0 / 9.0 | 0.00% | 54.757 / 59.664 s | −8.23% | 49.142 / 53.865 s |

Median paired decode-rate change was **0.00%**; NInfer was faster in only one
of three pairs. Median client-total latency change was −3.84%, and median TTFT
change was −3.90%, but both vary across pairs. The registered primary gate
requires at least 5% decode-rate improvement with all three pairs favoring
NInfer, so the screen **fails** and does not justify seven-pair confirmation.
No acceleration claim is made. Per-pair response, route, state and memory
details are in [`paired-summary.json`](paired-summary.json) and the campaign
directory.

One pre-registered check was not captured directly: these API runs did not emit
a resident-map file for each process. The preceding full staged-backend
functional ablation with the same model, profile and cache options recorded
identical map hashes for both backends. The measured runs here also had exact
state hashes and identical cache/staged-read counts, but this screen alone
cannot prove per-process map identity. That limitation further precludes
performance qualification; it does not change the failed decode-rate gate.

Configs, workload, randomized order, full request data and supervisor memory,
clock and tegrastats records remain beside this report. No clock or service
settings were changed.
